"""
Backtest execution engine for pairs trading.

This module provides the core trading simulation orchestration:
- Walk-forward backtesting
- Trading simulation loop
- Kalman filter hedge ratio wrapper

The heavy lifting is delegated to specialized modules:
- pair_selection.py: Cointegration testing, pair selection
- signal_generation.py: Z-score signals, stops, position sizing
- position_management.py: Position tracking, PnL, blacklisting
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .config import BacktestConfig
from .pair_selection import (
    select_pairs,
    run_engle_granger_test,
    monitor_cointegration_drift,
    update_hedge_ratio,
)
from .signal_generation import (
    calculate_time_based_stop,
    check_vix_regime,
    calculate_volatility_adjusted_size,
)
from .position_management import PairBlacklist
from ..utils.sectors import get_sector
from ..constants import MIN_FORMATION_DATA_PCT
from ..features.kalman_hedge import kalman_filter_hedge

logger = logging.getLogger(__name__)


# =============================================================================
# KALMAN FILTER WRAPPER
# =============================================================================

def estimate_kalman_hedge_ratio(
    series_x: pd.Series,
    series_y: pd.Series,
    use_log: bool = True,
    delta: float = 0.00001,
    vw: float = 0.001,
    use_momentum: bool = True,  # Parameter kept for compatibility but ignored
) -> Optional[pd.DataFrame]:
    """
    Estimate time-varying hedge ratio using Kalman Filter.

    This is a wrapper around features.kalman_hedge.kalman_filter_hedge()
    to maintain compatibility with existing code.

    NOTE: The use_momentum parameter is ignored - only the basic 2-state
    model is available after consolidation.

    Parameters
    ----------
    series_x : pd.Series
        Independent variable (price series)
    series_y : pd.Series
        Dependent variable (price series)
    use_log : bool
        Whether to use log prices
    delta : float
        Process noise scaling factor
    vw : float
        Initial observation noise variance
    use_momentum : bool
        DEPRECATED - Ignored for compatibility

    Returns
    -------
    pd.DataFrame or None
        DataFrame with columns: hedge_ratio, intercept, spread, hedge_ratio_var
    """
    if use_momentum:
        logger.debug("use_momentum=True ignored - momentum model was removed during cleanup")

    try:
        result = kalman_filter_hedge(
            price_x=series_x,
            price_y=series_y,
            delta=delta,
            Ve=vw,
            use_log=use_log,
        )
        return result.to_dataframe()
    except (ValueError, Exception) as e:
        logger.debug(f"Kalman filter failed: {e}")
        return None


# =============================================================================
# TRADING SIMULATION
# =============================================================================

def run_trading_simulation(
    prices: pd.DataFrame,
    pairs: List[Tuple[str, str]],
    hedge_ratios: Dict,
    half_lives: Dict,
    cfg: BacktestConfig,
    current_capital: float = None,
    optimal_deltas: Dict = None,
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Run trading simulation on selected pairs.

    Parameters
    ----------
    prices : pd.DataFrame
        Trading period price data
    pairs : list
        Selected pairs to trade
    hedge_ratios : dict
        Hedge ratios for each pair
    half_lives : dict
        Half-lives for each pair
    cfg : BacktestConfig
        Configuration
    current_capital : float, optional
        Current capital (for compounding mode)
    optimal_deltas : dict, optional
        Per-pair optimal entry thresholds

    Returns
    -------
    tuple
        (trades_list, ending_capital)
    """
    trades = []
    n_dates = len(prices)
    n_pairs = len(pairs)
    use_adaptive = getattr(cfg, 'use_adaptive_lookback', False)
    lb_min = getattr(cfg, 'adaptive_lookback_min', 30)
    lb_max = getattr(cfg, 'adaptive_lookback_max', cfg.zscore_lookback)
    warmup = max(30, lb_max if use_adaptive else cfg.zscore_lookback)

    if n_pairs == 0 or n_dates <= warmup:
        return trades, current_capital if current_capital else cfg.initial_capital

    # Capital management
    if current_capital is None:
        current_capital = cfg.initial_capital

    max_pos = cfg.max_positions if cfg.max_positions > 0 else len(pairs)
    pair_names = {pair: f"{pair[0]}_{pair[1]}" for pair in pairs}

    # State tracking
    position_state = {pair: 0 for pair in pairs}
    entry_data = {pair: {} for pair in pairs}
    current_hr = dict(hedge_ratios)

    # Calculate initial spreads
    spreads = pd.DataFrame(index=prices.index)
    for pair in pairs:
        leg_x, leg_y = pair
        hr = current_hr[pair]
        px, py = prices[leg_x], prices[leg_y]

        if (px <= 0).any() or (py <= 0).any():
            logger.warning(f"Invalid prices for {pair_names[pair]}, skipping")
            spreads[pair_names[pair]] = np.nan
            continue

        spreads[pair_names[pair]] = np.log(px) - hr * np.log(py)

    # Rolling z-score calculation
    if use_adaptive:
        mult = getattr(cfg, 'adaptive_lookback_multiplier', 4.0)
        rolling_mean = pd.DataFrame(index=prices.index)
        rolling_std = pd.DataFrame(index=prices.index)
        zscores = pd.DataFrame(index=prices.index)
        pair_lookbacks = {}

        for pair in pairs:
            pair_name = pair_names[pair]
            hl = half_lives[pair]
            lookback = int(max(lb_min, min(lb_max, mult * hl)))
            pair_lookbacks[pair] = lookback
            min_per = min(lookback, 30)

            spread_series = spreads[pair_name]
            rolling_mean[pair_name] = spread_series.rolling(window=lookback, min_periods=min_per).mean()
            rolling_std[pair_name] = spread_series.rolling(window=lookback, min_periods=min_per).std()
            std_vals = rolling_std[pair_name]
            zscores[pair_name] = (spread_series - rolling_mean[pair_name]) / std_vals.where(std_vals > 0, np.nan)
    else:
        rolling_mean = spreads.rolling(window=cfg.zscore_lookback, min_periods=30).mean()
        rolling_std = spreads.rolling(window=cfg.zscore_lookback, min_periods=30).std()
        zscores = (spreads - rolling_mean) / rolling_std

    # Hedge ratio methodology
    hedge_method = getattr(cfg, 'hedge_ratio_method', 'auto')
    method_normalized = hedge_method.strip().lower() if isinstance(hedge_method, str) else 'auto'
    use_kalman = getattr(cfg, 'use_kalman_hedge', False)
    use_dynamic_ols = getattr(cfg, 'dynamic_hedge', False)

    if method_normalized != 'auto':
        if method_normalized == 'kalman':
            use_kalman, use_dynamic_ols = True, False
        elif method_normalized in {'rolling', 'ols'}:
            use_dynamic_ols, use_kalman = True, False
        elif method_normalized == 'fixed':
            use_dynamic_ols = use_kalman = False

    # Pre-compute Kalman hedge ratios if enabled
    kalman_results = {}
    if use_kalman:
        logger.info("Computing Kalman filter hedge ratios...")
        for pair in pairs:
            leg_x, leg_y = pair
            kalman_df = estimate_kalman_hedge_ratio(
                prices[leg_x], prices[leg_y],
                use_log=cfg.use_log_prices,
                delta=getattr(cfg, 'kalman_delta', 0.00001),
                vw=getattr(cfg, 'kalman_vw', 0.001),
            )
            if kalman_df is not None:
                kalman_results[pair] = kalman_df

        # Update spreads with Kalman hedge ratios
        if kalman_results:
            for pair in pairs:
                if pair in kalman_results:
                    pair_name = pair_names[pair]
                    leg_x, leg_y = pair
                    kalman_hr = kalman_results[pair]['hedge_ratio']
                    log_x, log_y = np.log(prices[leg_x]), np.log(prices[leg_y])
                    common_idx = spreads.index.intersection(kalman_results[pair].index)
                    spreads.loc[common_idx, pair_name] = (
                        log_x.loc[common_idx] - kalman_hr.loc[common_idx] * log_y.loc[common_idx]
                    ).values

            # Recalculate z-scores
            rolling_mean = spreads.rolling(window=cfg.zscore_lookback, min_periods=30).mean()
            rolling_std = spreads.rolling(window=cfg.zscore_lookback, min_periods=30).std()
            zscores = (spreads - rolling_mean) / rolling_std

    dates = prices.index.tolist()

    # Main trading loop
    for t in range(warmup + 1, n_dates):
        current_date = dates[t]
        signal_date = dates[t - 1]

        # Update Kalman hedge ratios for flat positions
        if use_kalman:
            for pair in pairs:
                if pair in kalman_results and current_date in kalman_results[pair].index:
                    if position_state[pair] == 0:
                        kalman_hr = kalman_results[pair].loc[current_date, 'hedge_ratio']
                        if not np.isnan(kalman_hr):
                            current_hr[pair] = kalman_hr

        # Dynamic OLS hedge ratio update
        elif use_dynamic_ols and t % cfg.hedge_update_days == 0 and t > cfg.hedge_update_days:
            for pair in pairs:
                try:
                    new_hr, _ = update_hedge_ratio(
                        prices.iloc[:t], pair,
                        lookback=cfg.hedge_update_days,
                        use_log=cfg.use_log_prices
                    )
                    if position_state[pair] == 0:
                        current_hr[pair] = new_hr
                        leg_x, leg_y = pair
                        spreads[pair_names[pair]] = np.log(prices[leg_x].iloc[:t]) - new_hr * np.log(prices[leg_y].iloc[:t])
                except Exception:
                    pass

            # Recalculate z-scores
            if use_adaptive:
                for pair in pairs:
                    pair_name = pair_names[pair]
                    lookback = pair_lookbacks[pair]
                    min_per = min(lookback, 30)
                    spread_series = spreads[pair_name]
                    rolling_mean[pair_name] = spread_series.rolling(window=lookback, min_periods=min_per).mean()
                    rolling_std[pair_name] = spread_series.rolling(window=lookback, min_periods=min_per).std()
                    zscores[pair_name] = (spread_series - rolling_mean[pair_name]) / rolling_std[pair_name].where(rolling_std[pair_name] > 0, np.nan)
            else:
                rolling_mean = spreads.rolling(window=cfg.zscore_lookback, min_periods=30).mean()
                rolling_std = spreads.rolling(window=cfg.zscore_lookback, min_periods=30).std()
                zscores = (spreads - rolling_mean) / rolling_std

        # === CHECK EXITS ===
        for pair in pairs:
            if position_state[pair] == 0:
                continue

            pair_name = pair_names[pair]
            direction = position_state[pair]
            entry = entry_data[pair]

            # Calculate z-score (with fixed exit params if enabled)
            if getattr(cfg, 'use_fixed_exit_params', True):
                leg_x, leg_y = pair
                log_x = np.log(prices.loc[signal_date, leg_x])
                log_y = np.log(prices.loc[signal_date, leg_y])
                hr_entry = entry.get('hr', current_hr[pair])
                spread = log_x - hr_entry * log_y
                mu_entry = entry.get('mu_entry', rolling_mean.loc[signal_date, pair_name])
                sigma_entry = entry.get('sigma_entry', rolling_std.loc[signal_date, pair_name])
                z = (spread - mu_entry) / sigma_entry if sigma_entry > 0 else 0.0
            else:
                spread = spreads.loc[signal_date, pair_name]
                z = zscores.loc[signal_date, pair_name]

            if pd.isna(z):
                continue

            should_exit = False
            exit_reason = None
            holding_days = t - entry['t']
            hl = half_lives[pair]

            # Cointegration drift monitoring
            if not should_exit and getattr(cfg, 'enable_cointegration_monitoring', False):
                check_freq = getattr(cfg, 'coint_check_frequency_days', 21)
                if holding_days > 0 and holding_days % check_freq == 0:
                    lookback = getattr(cfg, 'coint_drift_lookback_days', 60)
                    pval_threshold = getattr(cfg, 'coint_drift_pvalue_threshold', 0.15)
                    min_obs = getattr(cfg, 'coint_drift_min_observations', 30)
                    history_start = max(0, t - lookback)
                    recent_prices = prices.iloc[history_start:t+1]

                    if len(recent_prices) >= min_obs:
                        drift_status = monitor_cointegration_drift(
                            prices=recent_prices, pair=pair,
                            lookback_days=lookback, pvalue_threshold=pval_threshold,
                            min_observations=min_obs, use_log=True
                        )
                        if drift_status['drift_detected']:
                            should_exit = True
                            exit_reason = 'cointegration_drift'
                            logger.info(f"[DRIFT] {pair_names[pair]}: p={drift_status['pvalue']:.4f}")

            # Max holding check
            if cfg.dynamic_max_holding:
                max_hold = int(np.ceil(getattr(cfg, 'max_holding_multiplier', 3.0) * hl))
                dyn_cap = getattr(cfg, 'max_dynamic_holding_days', 0)
                if dyn_cap > 0:
                    max_hold = min(max_hold, dyn_cap)
                max_hold = max(1, max_hold)
            else:
                max_hold = cfg.max_holding_days

            if not should_exit and holding_days >= max_hold:
                should_exit = True
                exit_reason = "max_holding"

            # Dynamic Z exit
            if not should_exit and getattr(cfg, 'use_dynamic_z_exit', False):
                hl_ratio = getattr(cfg, 'dynamic_z_exit_hl_ratio', 1.5)
                z_thresh = getattr(cfg, 'dynamic_z_exit_threshold', 0.0)
                if holding_days >= hl_ratio * hl:
                    if abs(z) >= abs(entry.get('z', 0)) + z_thresh:
                        should_exit = True
                        exit_reason = "z_diverging"

            # Slow convergence exit
            if not should_exit and getattr(cfg, 'use_slow_convergence_exit', False):
                sc_hl_ratio = getattr(cfg, 'slow_conv_hl_ratio', 1.5)
                sc_z_pct = getattr(cfg, 'slow_conv_z_pct', 0.50)
                if holding_days >= sc_hl_ratio * hl:
                    entry_z_abs = abs(entry.get('z', 0))
                    if entry_z_abs > 0 and abs(z) / entry_z_abs > sc_z_pct:
                        should_exit = True
                        exit_reason = "slow_convergence"

            # Regime break check
            if not should_exit:
                if use_kalman and getattr(cfg, 'kalman_zscore_regime', True):
                    kalman_regime_z = getattr(cfg, 'kalman_regime_zscore', 3.0)
                    entry_z_val = entry.get('z', 0)
                    if (direction == 1 and z <= entry_z_val - kalman_regime_z) or \
                       (direction == -1 and z >= entry_z_val + kalman_regime_z):
                        should_exit = True
                        exit_reason = "regime_break"
                elif entry['spread'] * spread < 0:
                    should_exit = True
                    exit_reason = "regime_break"

            # Convergence and stop-loss
            if not should_exit:
                exit_tol = getattr(cfg, 'exit_tolerance_sigma', 0.1)
                exit_thresh = getattr(cfg, 'exit_threshold_sigma', 0.0)
                base_stop = getattr(cfg, 'stop_loss_sigma', 4.0)
                use_adaptive_stop = getattr(cfg, 'use_adaptive_stop_loss', False)

                if use_adaptive_stop:
                    hl_factor = (hl / 10.0) - 1.0
                    stop_sigma = max(3.0, min(5.0, base_stop + 0.5 * hl_factor))
                else:
                    stop_sigma = base_stop

                if direction == 1:  # Long spread
                    if z >= -(exit_thresh + exit_tol):
                        should_exit = True
                        exit_reason = "convergence"
                    else:
                        use_time_stops = getattr(cfg, 'time_based_stops', True)
                        if use_time_stops:
                            tightening_rate = getattr(cfg, 'stop_tightening_rate', 0.15)
                            time_stop, _ = calculate_time_based_stop(
                                entry['z'], z, holding_days, hl, stop_sigma, tightening_rate
                            )
                            if time_stop:
                                should_exit = True
                                exit_reason = "stop_loss_time"
                        elif z <= -stop_sigma:
                            should_exit = True
                            exit_reason = "stop_loss"
                else:  # Short spread
                    if z <= (exit_thresh + exit_tol):
                        should_exit = True
                        exit_reason = "convergence"
                    else:
                        use_time_stops = getattr(cfg, 'time_based_stops', True)
                        if use_time_stops:
                            tightening_rate = getattr(cfg, 'stop_tightening_rate', 0.15)
                            time_stop, _ = calculate_time_based_stop(
                                entry['z'], z, holding_days, hl, stop_sigma, tightening_rate
                            )
                            if time_stop:
                                should_exit = True
                                exit_reason = "stop_loss_time"
                        elif z >= stop_sigma:
                            should_exit = True
                            exit_reason = "stop_loss"

            # Execute exit
            if should_exit:
                leg_x, leg_y = pair
                px = prices.loc[current_date, leg_x]
                py = prices.loc[current_date, leg_y]

                pnl_x = entry['qty_x'] * (px - entry['px'])
                pnl_y = entry['qty_y'] * (py - entry['py'])
                pnl = pnl_x + pnl_y

                entry_notional = abs(entry['qty_x']) * entry['px'] + abs(entry['qty_y']) * entry['py']
                exit_notional = abs(entry['qty_x']) * px + abs(entry['qty_y']) * py
                cost = (entry_notional + exit_notional) * (cfg.transaction_cost_bps / 10000)
                pnl -= cost

                trades.append({
                    'pair': pair, 'leg_x': leg_x, 'leg_y': leg_y,
                    'sector': get_sector(leg_x),
                    'direction': 'LONG' if direction == 1 else 'SHORT',
                    'entry_date': entry['date'], 'exit_date': current_date,
                    'holding_days': holding_days,
                    'entry_z': entry['z'], 'exit_z': z,
                    'hedge_ratio': entry['hr'], 'half_life': hl,
                    'pnl': pnl, 'exit_reason': exit_reason,
                    'capital_at_entry': entry.get('capital', current_capital),
                    'qty_x': entry['qty_x'], 'qty_y': entry['qty_y'],
                    'entry_px': entry['px'], 'entry_py': entry['py'],
                })

                if cfg.compounding:
                    current_capital += pnl

                position_state[pair] = 0
                entry_data[pair] = {}

        # === CHECK ENTRIES ===
        n_active = sum(1 for p in pairs if position_state[p] != 0)
        max_pos_limit = cfg.max_positions if cfg.max_positions > 0 else len(pairs)

        # VIX regime filter
        skip_entries = False
        if getattr(cfg, 'use_vix_filter', False):
            vix_col = 'VIX' if 'VIX' in prices.columns else ('^VIX' if '^VIX' in prices.columns else None)
            if vix_col:
                vix_info = check_vix_regime(
                    prices[vix_col], current_date,
                    getattr(cfg, 'vix_threshold', 30.0),
                    getattr(cfg, 'vix_lookback_days', 5)
                )
                skip_entries = vix_info['is_high_vol']

        if n_active < max_pos_limit and not skip_entries:
            for pair in pairs:
                if position_state[pair] != 0 or n_active >= max_pos_limit:
                    continue

                pair_name = pair_names[pair]
                z = zscores.loc[signal_date, pair_name]
                spread = spreads.loc[signal_date, pair_name]

                if pd.isna(z):
                    continue

                leg_x, leg_y = pair
                px = prices.loc[current_date, leg_x]
                py = prices.loc[current_date, leg_y]
                hr = current_hr[pair]

                # Calculate position capital
                if cfg.compounding:
                    max_pos = cfg.max_positions if cfg.max_positions > 0 else max(5, len(pairs))
                    position_capital = (current_capital * cfg.leverage) / max(1, max_pos)
                    if cfg.max_capital_per_trade > 0:
                        position_capital = min(position_capital, cfg.max_capital_per_trade)
                else:
                    position_capital = cfg.capital_per_pair * cfg.leverage

                # Volatility-adjusted sizing
                if getattr(cfg, 'use_vol_sizing', False):
                    spread_changes = spreads[pair_name].diff().dropna()
                    if len(spread_changes) >= 20:
                        spread_vol = spread_changes.iloc[-20:].std()
                        position_capital = calculate_volatility_adjusted_size(
                            position_capital, spread_vol,
                            getattr(cfg, 'target_daily_vol', 0.02),
                            getattr(cfg, 'vol_size_min', 0.25),
                            getattr(cfg, 'vol_size_max', 2.0),
                        )

                notional_x = position_capital / (1 + abs(hr))
                notional_y = abs(hr) * notional_x

                # Entry threshold
                if optimal_deltas and pair in optimal_deltas:
                    entry_thresh = optimal_deltas[pair]
                else:
                    entry_thresh = getattr(cfg, 'entry_threshold_sigma', 0.75)

                # Check entry signals
                if z <= -entry_thresh:
                    position_state[pair] = 1
                    entry_data[pair] = {
                        't': t, 'date': current_date, 'signal_date': signal_date,
                        'z': z, 'spread': spread, 'px': px, 'py': py, 'hr': hr,
                        'qty_x': notional_x / px, 'qty_y': -notional_y / py,
                        'capital': current_capital,
                        'mu_entry': rolling_mean.loc[signal_date, pair_name],
                        'sigma_entry': rolling_std.loc[signal_date, pair_name],
                    }
                    n_active += 1
                elif z >= entry_thresh:
                    position_state[pair] = -1
                    entry_data[pair] = {
                        't': t, 'date': current_date, 'signal_date': signal_date,
                        'z': z, 'spread': spread, 'px': px, 'py': py, 'hr': hr,
                        'qty_x': -notional_x / px, 'qty_y': notional_y / py,
                        'capital': current_capital,
                        'mu_entry': rolling_mean.loc[signal_date, pair_name],
                        'sigma_entry': rolling_std.loc[signal_date, pair_name],
                    }
                    n_active += 1

    # Close remaining positions
    last_date = dates[-1]
    for pair in pairs:
        if position_state[pair] == 0:
            continue

        direction = position_state[pair]
        entry = entry_data[pair]
        leg_x, leg_y = pair
        pair_name = pair_names[pair]

        px = prices.loc[last_date, leg_x]
        py = prices.loc[last_date, leg_y]

        # Calculate exit z-score
        if getattr(cfg, 'use_fixed_exit_params', True):
            log_x, log_y = np.log(px), np.log(py)
            hr_entry = entry.get('hr', current_hr[pair])
            spread = log_x - hr_entry * log_y
            mu_entry = entry.get('mu_entry', rolling_mean.loc[last_date, pair_name])
            sigma_entry = entry.get('sigma_entry', rolling_std.loc[last_date, pair_name])
            z = (spread - mu_entry) / sigma_entry if sigma_entry > 0 else 0.0
        else:
            z_val = zscores.loc[last_date, pair_name]
            z = z_val if not pd.isna(z_val) else 0

        pnl_x = entry['qty_x'] * (px - entry['px'])
        pnl_y = entry['qty_y'] * (py - entry['py'])
        pnl = pnl_x + pnl_y

        entry_notional = abs(entry['qty_x']) * entry['px'] + abs(entry['qty_y']) * entry['py']
        exit_notional = abs(entry['qty_x']) * px + abs(entry['qty_y']) * py
        cost = (entry_notional + exit_notional) * (cfg.transaction_cost_bps / 10000)
        pnl -= cost

        holding_days = max(1, len(prices) - 1 - entry['t'])

        trades.append({
            'pair': pair, 'leg_x': leg_x, 'leg_y': leg_y,
            'sector': get_sector(leg_x),
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_date': entry['date'], 'exit_date': last_date,
            'holding_days': holding_days,
            'entry_z': entry['z'], 'exit_z': z,
            'hedge_ratio': entry['hr'], 'half_life': half_lives[pair],
            'pnl': pnl, 'exit_reason': 'period_end',
            'capital_at_entry': entry.get('capital', current_capital),
            'qty_x': entry['qty_x'], 'qty_y': entry['qty_y'],
            'entry_px': entry['px'], 'entry_py': entry['py'],
        })

        if cfg.compounding:
            current_capital += pnl

    return trades, current_capital


# =============================================================================
# WALK-FORWARD BACKTEST
# =============================================================================

def run_walkforward_backtest(
    prices: pd.DataFrame,
    cfg: BacktestConfig,
    start_year: int = 2010,
    end_year: int = 2024,
) -> Tuple[List[Dict], pd.DataFrame]:
    """
    Run walk-forward backtest across multiple years.

    Parameters
    ----------
    prices : pd.DataFrame
        Full price data
    cfg : BacktestConfig
        Configuration
    start_year : int
        First trading year
    end_year : int
        Last trading year

    Returns
    -------
    tuple
        (all_trades, yearly_summary)
    """
    all_trades = []
    year_results = []

    blacklist = PairBlacklist(cfg.blacklist_stoploss_rate, cfg.blacklist_min_trades)
    current_capital = cfg.initial_capital

    for trading_year in range(start_year, end_year + 1):
        formation_year = trading_year - 1

        logger.info("=" * 60)
        logger.info(f"Year {trading_year}: Formation {formation_year}")
        if cfg.compounding:
            logger.info(f"Current Capital: ${current_capital:,.2f}")
        logger.info("=" * 60)

        # Formation period
        formation_start = pd.Timestamp(f'{formation_year}-01-01')
        formation_end = pd.Timestamp(f'{formation_year}-12-31')

        mask = (prices.index >= formation_start) & (prices.index <= formation_end)
        formation_prices = prices.loc[mask]
        if formation_prices.isna().values.any():
            missing = formation_prices.isna().mean()
            cols = missing[missing <= 0.20].index
            formation_prices = formation_prices[cols].ffill().bfill()
        else:
            formation_prices = formation_prices.copy()

        if len(formation_prices) < cfg.formation_days * MIN_FORMATION_DATA_PCT:
            logger.warning(f"Insufficient formation data for {trading_year}")
            continue

        # Select pairs
        t0 = time.time()
        pairs, hedge_ratios, half_lives, formation_stats, optimal_deltas = select_pairs(
            formation_prices, cfg, blacklist.blacklist
        )
        logger.info(f"Pair selection: {time.time() - t0:.2f}s")

        if not pairs:
            logger.warning(f"No pairs selected for {trading_year}")
            continue

        # Trading period
        trading_start = pd.Timestamp(f'{trading_year}-01-01')
        trading_end = pd.Timestamp(f'{trading_year}-12-31')

        mask = (prices.index >= trading_start) & (prices.index <= trading_end)
        trading_prices = prices.loc[mask]

        # Keep valid tickers
        valid_tickers = set()
        for pair in pairs:
            valid_tickers.add(pair[0])
            valid_tickers.add(pair[1])
        valid_tickers = [t for t in valid_tickers if t in trading_prices.columns]
        trading_prices = trading_prices[valid_tickers].dropna(axis=1, how='any')

        pairs = [p for p in pairs if p[0] in trading_prices.columns and p[1] in trading_prices.columns]

        if not pairs:
            continue

        if len(pairs) < cfg.min_pairs_for_trading:
            logger.warning(f"Only {len(pairs)} pairs (min: {cfg.min_pairs_for_trading}), skipping {trading_year}")
            continue

        # Run simulation
        trades, current_capital = run_trading_simulation(
            trading_prices, pairs, hedge_ratios, half_lives, cfg, current_capital, optimal_deltas
        )

        blacklist.update(trades)

        # Calculate stats
        n_trades = len(trades)
        n_wins = sum(1 for t in trades if t['pnl'] > 0)
        total_pnl = sum(t['pnl'] for t in trades)

        exit_reasons = defaultdict(int)
        for t in trades:
            exit_reasons[t['exit_reason']] += 1

        logger.info(f"Pairs: {len(pairs)}, Trades: {n_trades}, PnL: ${total_pnl:.2f}")
        logger.info(f"Exit reasons: {dict(exit_reasons)}")

        year_results.append({
            'trading_year': trading_year,
            'pairs_selected': len(pairs),
            'total_trades': n_trades,
            'winning_trades': n_wins,
            'win_rate': n_wins / n_trades * 100 if n_trades > 0 else 0,
            'total_pnl': total_pnl,
            'ending_capital': current_capital if cfg.compounding else None,
            **{f'{k}_exits': v for k, v in exit_reasons.items()},
        })

        all_trades.extend(trades)

    summary_df = pd.DataFrame(year_results)
    return all_trades, summary_df
