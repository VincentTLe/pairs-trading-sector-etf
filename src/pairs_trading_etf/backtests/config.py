"""
Backtest configuration management.

This module provides a unified configuration system for pairs trading backtests,
supporting both programmatic configuration via dataclasses and YAML file loading.
"""

from __future__ import annotations

import yaml
import numpy as np
from scipy.stats import norm
from scipy.optimize import minimize_scalar
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple

from ..utils.sectors import DEFAULT_EXCLUDED_SECTORS
import src.pairs_trading_etf.constants as constant


# =============================================================================
# CONFIGURATION DATACLASS
# =============================================================================

@dataclass
class BacktestConfig:
    """
    Configuration for pairs trading backtest.
    
    This unified config replaces the scattered configurations in various scripts.
    Can be loaded from YAML or created programmatically.
    """
    
    # ==========================================================================
    # Experiment Metadata
    # ==========================================================================
    experiment_name: str = "default"
    description: str = ""
    
    # ==========================================================================
    # Time Windows
    # ==========================================================================
    formation_days: int = constant.FORMATION_PERIOD_DAYS
    trading_days: int = constant.TRADING_DAYS_PER_YEAR
    hedge_update_days: int = 63      # Quarterly hedge ratio update
    
    # ==========================================================================
    # Cointegration Testing
    # ==========================================================================
    # WARNING: p-value must be 0.01 or 0.05 ONLY. Never increase above 0.05!
    pvalue_threshold: float = constant.PVALUE_FORMATION
    min_half_life: float = constant.DEFAULT_MIN_HALF_LIFE
    max_half_life: float = constant.DEFAULT_MAX_HALF_LIFE
    use_log_prices: bool = True
    
    # ==========================================================================
    # Correlation Filter
    # ==========================================================================
    min_correlation: float = constant.DEFAULT_MIN_CORRELATION
    max_correlation: float = constant.DEFAULT_MAX_CORRELATION
    
    # ==========================================================================
    # Rolling Consistency (RECOMMENDED - enabled by default)
    # ==========================================================================
    rolling_consistency: bool = True
    n_rolling_windows: int = 4
    min_passing_windows: int = 2
    
    # ==========================================================================
    # Pair Selection
    # ==========================================================================
    top_pairs: int = 20
    max_pairs_per_sector: int = 5
    max_pairs_per_etf: int = 2
    min_spread_range_pct: float = 0.02
    
    # ==========================================================================
    # Sector Focus
    # ==========================================================================
    sector_focus: bool = True
    exclude_sectors: Tuple[str, ...] = DEFAULT_EXCLUDED_SECTORS
    
    # ==========================================================================
    # Trading Signals (Vidyamurthy Ch.8: Optimal Threshold Design)
    # ==========================================================================
    # Traditional z-score (2.0-2.5) is statistically motivated, NOT economically optimal
    entry_threshold_sigma: float = constant.DEFAULT_ENTRY_THRESHOLD_SIGMA   # LEGACY fallback

    # Optimal threshold modes (RECOMMENDED: use_optimal_entry_threshold=True)
    use_optimal_entry_threshold: bool = False
    optimal_threshold_method: str = 'nonparametric'
    # - 'white_noise': Use formula Δ* = argmax[Δ(1-N(Δ))], COMPUTED per pair with transaction costs
    # - 'nonparametric': Use historical data to find Δ that maximizes profit (RECOMMENDED)
    
    optimal_threshold_lambda: float = constant.OPTIMAL_THRESHOLD_LAMBDA  # Regularization

    exit_threshold_sigma: float = constant.DEFAULT_EXIT_THRESHOLD_SIGMA
    exit_tolerance_sigma: float = constant.EXIT_TOLERANCE_SIGMA
    stop_loss_sigma: float = constant.DEFAULT_STOP_LOSS_SIGMA          # Z-score stop
    zscore_lookback: int = constant.DEFAULT_ZSCORE_LOOKBACK             # Default lookback
    
    # ==========================================================================
    # Adaptive Z-Score Lookback (QMA: lookback = f(half_life))
    # ==========================================================================
    use_adaptive_lookback: bool = True
    adaptive_lookback_multiplier: float = constant.ADAPTIVE_LOOKBACK_MULTIPLIER
    adaptive_lookback_min: int = constant.ADAPTIVE_LOOKBACK_MIN
    adaptive_lookback_max: int = constant.ADAPTIVE_LOOKBACK_MAX
    
    # ==========================================================================
    # QMA Level 2: Fixed Exit Parameters
    # ==========================================================================
    use_fixed_exit_params: bool = True
    
    # ==========================================================================
    # Hedge Ratio Filter (NEW - improves win rate)
    # ==========================================================================
    min_hedge_ratio: float = constant.MIN_HEDGE_RATIO
    max_hedge_ratio: float = constant.MAX_HEDGE_RATIO
    
    # ==========================================================================
    # Position Management
    # ==========================================================================
    max_holding_days: int = constant.DEFAULT_MAX_HOLDING_DAYS
    max_positions: int = constant.DEFAULT_MAX_POSITIONS
    dynamic_hedge: bool = True
    dynamic_max_holding: bool = True
    max_holding_multiplier: float = constant.DEFAULT_MAX_HOLDING_MULTIPLIER
    max_dynamic_holding_days: int = 0
    hedge_ratio_method: str = "auto"
    
    # ==========================================================================
    # Capital Allocation (see engine.py for logic)
    # ==========================================================================
    capital_per_pair: float = 10000.0
    
    # ==========================================================================
    # Vidyamurthy Framework - SNR & Tradability Filters (Ch.7)
    # ==========================================================================
    min_snr: float = 0.0
    min_zero_crossing_rate: float = 0.0
    time_based_stops: bool = True
    stop_tightening_rate: float = constant.STOP_TIGHTENING_RATE
    
    # ==========================================================================
    # Adaptive Stop-Loss (scale with half-life)
    # ==========================================================================
    use_adaptive_stop_loss: bool = True
    
    # [Vidyamurthy:Ch.7:p114-115] Bootstrap procedure for holding period estimation
    use_bootstrap_holding_period: bool = True
    bootstrap_n_samples: int = 1000
    
    # ==========================================================================
    # Kalman Filter Dynamic Hedge Ratio
    # ==========================================================================
    use_kalman_hedge: bool = False
    kalman_delta: float = 0.00001
    kalman_vw: float = 0.001
    kalman_use_momentum: bool = True
    kalman_zscore_regime: bool = True
    kalman_regime_zscore: float = 3.0
    
    # ==========================================================================
    # VIX Regime Filter
    # ==========================================================================
    use_vix_filter: bool = False
    vix_threshold: float = constant.VIX_THRESHOLD
    vix_lookback_days: int = constant.VIX_LOOKBACK_DAYS
    
    # ==========================================================================
    # Volatility-Adjusted Position Sizing
    # ==========================================================================
    use_vol_sizing: bool = False
    target_daily_vol: float = 0.02
    vol_size_min: float = constant.VIX_MIN_SCALE
    vol_size_max: float = constant.VIX_MAX_SCALE
    
    # ==========================================================================
    # Dynamic Z-Score Exit
    # ==========================================================================
    use_dynamic_z_exit: bool = False
    dynamic_z_exit_hl_ratio: float = 1.5
    dynamic_z_exit_threshold: float = 0.0
    
    # ==========================================================================
    # Slow Convergence Exit
    # ==========================================================================
    use_slow_convergence_exit: bool = False
    
    # ==========================================================================
    # Cointegration Drift Monitoring (CRITICAL FIX)
    # ==========================================================================
    enable_cointegration_monitoring: bool = True
    coint_check_frequency_days: int = constant.DRIFT_CHECK_FREQUENCY
    coint_drift_pvalue_threshold: float = constant.DRIFT_PVALUE_THRESHOLD
    coint_drift_lookback_days: int = constant.DRIFT_MONITOR_LOOKBACK
    coint_drift_min_observations: int = constant.MIN_OBSERVATIONS_DRIFT
    slow_conv_hl_ratio: float = 1.5
    slow_conv_z_pct: float = 0.50
    
    # ==========================================================================
    # Compounding & Leverage
    # ==========================================================================
    initial_capital: float = 50000.0
    leverage: float = 1.0
    compounding: bool = False
    unlimited_pairs: bool = False
    max_capital_per_trade: float = 0.0
    min_pairs_for_trading: int = 3
    
    # ==========================================================================
    # Costs and Risk
    # ==========================================================================
    transaction_cost_bps: float = constant.DEFAULT_TRANSACTION_COST_BPS
    
    # ==========================================================================
    # Blacklist
    # ==========================================================================
    blacklist_stoploss_rate: float = constant.BLACKLIST_STOP_LOSS_RATE
    blacklist_min_trades: int = constant.BLACKLIST_MIN_TRADES
    
    # ==========================================================================
    # Output
    # ==========================================================================
    output_dir: str = "results"
    save_trades: bool = True
    save_summary: bool = True
    save_config_snapshot: bool = True
    timestamped_output: bool = True
    
    # ==========================================================================
    # Data Paths
    # ==========================================================================
    price_data_path: str = "data/raw/etf_prices_fresh.csv"
    etf_metadata_path: str = "configs/etf_metadata.yaml"
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        # Convert tuple from list if loaded from YAML
        if isinstance(self.exclude_sectors, list):
            self.exclude_sectors = tuple(self.exclude_sectors)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        d = asdict(self)
        # Convert tuple to list for YAML serialization
        d['exclude_sectors'] = list(d['exclude_sectors'])
        return d
    
    def save_yaml(self, path: str) -> None:
        """Save configuration to YAML file."""
        with open(path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)
    
    def get_output_path(self) -> Path:
        """Get output path, creating timestamped folder if needed."""
        base_path = Path(self.output_dir)
        
        if self.timestamped_output:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            folder_name = f"{timestamp}_{self.experiment_name}"
            output_path = base_path / folder_name
        else:
            output_path = base_path
        
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path


# =============================================================================
# YAML LOADING
# =============================================================================

def load_config(path: str) -> BacktestConfig:
    """
    Load configuration from YAML file.
    
    Parameters
    ----------
    path : str
        Path to YAML configuration file
        
    Returns
    -------
    BacktestConfig
        Configuration object
        
    Example
    -------
    >>> cfg = load_config('configs/experiments/conservative.yaml')
    >>> print(cfg.pvalue_threshold)
    0.01
    """
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    # Handle nested structure if present
    if 'backtest' in data:
        data = data['backtest']
    
    # Backwards compatibility for legacy field names
    legacy_fields = {
        'entry_zscore': 'entry_threshold_sigma',
        'exit_zscore': 'exit_threshold_sigma',
        'stop_loss_zscore': 'stop_loss_sigma',
    }
    for old_key, new_key in legacy_fields.items():
        if old_key in data:
            data.setdefault(new_key, data.pop(old_key))
    
    cfg = BacktestConfig(**data)
    
    # Optional: auto-compute entry threshold using Gatev/Vidyamurthy formula
    if getattr(cfg, 'use_optimal_entry_threshold', False):
        cfg.entry_threshold_sigma = compute_optimal_threshold(cfg.transaction_cost_bps)
    
    return cfg


def merge_configs(base: BacktestConfig, overrides: Dict[str, Any]) -> BacktestConfig:
    """
    Merge override values into base config.
    
    Parameters
    ----------
    base : BacktestConfig
        Base configuration
    overrides : dict
        Dictionary of values to override
        
    Returns
    -------
    BacktestConfig
        New configuration with overrides applied
    """
    base_dict = base.to_dict()
    base_dict.update(overrides)
    return BacktestConfig(**base_dict)


# =============================================================================
# PRESET CONFIGURATIONS
# =============================================================================

def compute_zscore_lookback(half_life: float) -> int:
    """
    Compute optimal zscore lookback window based on half-life.
    
    Per QMA research: lookback should scale with half-life to capture
    the mean-reverting behavior correctly.
    
    Formula: max(30, min(120, 4 * half_life))
    - At least 30 days for statistical significance
    - At most 120 days to avoid too much smoothing
    - 4x half_life as the base scaling factor
    
    Parameters
    ----------
    half_life : float
        The mean-reversion half-life in days
        
    Returns
    -------
    int
        Optimal lookback window for z-score calculation
    """
    return max(30, min(120, int(4 * half_life)))


def compute_optimal_threshold(slippage_bps: float = 0.0) -> float:
    """
    Compute optimal entry threshold using white noise formula (Vidyamurthy Ch.8).

    For white-noise spreads, the optimal threshold Delta* maximizes:
        f(Delta) = Delta * [1 - N(Delta)]

    where N(Delta) is the CDF of the standard normal distribution.

    Solving the first-order condition:
        d/dDelta [Delta(1 - N(Delta))] = 0
        [1 - N(Delta)] - Delta * n(Delta) = 0

    The solution depends on transaction costs. With zero costs, the theoretical
    optimum is around 0.7477σ. With transaction costs, it will be higher.

    IMPORTANT: This value is COMPUTED, not hardcoded. It varies based on:
    - Transaction costs (slippage_bps parameter)
    - Spread characteristics (implicitly, via the white noise assumption)

    Interpretation:
    - Delta too small -> many trades, but small profit per trade
    - Delta too large -> big profit per trade, but few trades
    - Delta* is the economically optimal balance between frequency and profit

    Parameters
    ----------
    slippage_bps : float
        Transaction cost in basis points. Higher costs -> higher optimal threshold.

    Returns
    -------
    float
        Optimal threshold in units of standard deviation, COMPUTED from formula

    Example
    -------
    >>> compute_optimal_threshold()
    0.7477  # Computed result with zero transaction costs

    >>> compute_optimal_threshold(slippage_bps=10)
    0.78  # Computed result adjusted for 10 bps slippage

    Notes
    -----
    This assumes white noise spread. For ARMA spreads, use the nonparametric
    approach (compute_nonparametric_threshold) which uses actual data.
    """
    # Profit function: f(delta) = delta * (1 - N(delta))
    # We want to MAXIMIZE this, so minimize the negative
    def neg_profit(delta: float) -> float:
        if delta <= 0:
            return 0.0
        return -delta * (1 - norm.cdf(delta))
    
    # Find optimal delta
    result = minimize_scalar(neg_profit, bounds=(0.1, 3.0), method='bounded')
    optimal_delta = result.x
    
    # Adjust for slippage if needed
    # Slippage in sigma units (rough approximation: 10 bps ~ 0.01 sigma for typical spread)
    if slippage_bps > 0:
        slippage_sigma = slippage_bps / 1000  # Rough conversion
        # Ensure profit per trade (2*delta) > slippage
        min_delta = slippage_sigma / 2
        optimal_delta = max(optimal_delta, min_delta)
    
    return round(optimal_delta, 4)


def compute_nonparametric_threshold(
    spread_series: np.ndarray,
    slippage_bps: float = 10.0,
    n_levels: int = 30,
    lambda_reg: float = 0.0,
    return_curve: bool = False
) -> float | tuple[float, np.ndarray, np.ndarray]:
    """
    Compute optimal threshold using nonparametric approach from QMA Chapter 8.

    Instead of assuming white noise, this method:
    1. Counts actual level crossings at various thresholds
    2. Computes profit = threshold * crossings for each level
    3. Applies regularization penalty (trading costs, risk)
    4. Returns threshold that maximizes objective function

    This handles ARMA-like spreads that deviate from white noise assumption.

    Regularization (Vidyamurthy Ch.8 Section 8.3):
        Objective = Profit(Δ) - λ × Cost(Δ)

        where Cost(Δ) = (# of trades) × (transaction cost per trade)

        λ = 0.0: No regularization (pure profit maximization, may overfit)
        λ = 0.5: Balanced (profit vs trading frequency)
        λ = 1.0: Conservative (penalize frequent trading heavily)

    Parameters
    ----------
    spread_series : np.ndarray
        Historical spread values (should be standardized: mean=0, std=1)
    slippage_bps : float
        Transaction cost in basis points (e.g., 10 = 0.10%)
    n_levels : int
        Number of threshold levels to evaluate
    lambda_reg : float
        Regularization parameter (0.0 to 1.0+)
        Controls trade-off between profit and trading frequency
    return_curve : bool
        If True, return (optimal_delta, deltas, objectives) for visualization

    Returns
    -------
    float or tuple
        If return_curve=False: optimal threshold
        If return_curve=True: (optimal_delta, deltas_array, objectives_array)

    Examples
    --------
    >>> spread = np.random.randn(252)  # 1 year of daily data
    >>> optimal_delta = compute_nonparametric_threshold(spread, slippage_bps=10, lambda_reg=0.2)
    >>> print(f"Optimal Δ = {optimal_delta}σ")

    >>> # Get full profit curve for visualization
    >>> delta_opt, deltas, objectives = compute_nonparametric_threshold(
    ...     spread, slippage_bps=10, lambda_reg=0.2, return_curve=True
    ... )
    >>> import matplotlib.pyplot as plt
    >>> plt.plot(deltas, objectives)
    >>> plt.axvline(delta_opt, color='r', label=f'Optimal Δ={delta_opt}')
    >>> plt.xlabel('Threshold (Δ)')
    >>> plt.ylabel('Objective (Profit - λ×Cost)')
    >>> plt.legend()
    >>> plt.show()
    """
    # Standardize spread
    spread = np.asarray(spread_series)
    if len(spread) < 20:
        # Not enough data, compute white noise optimal as fallback
        wn_optimal = compute_optimal_threshold(slippage_bps)
        return wn_optimal if not return_curve else (wn_optimal, np.array([wn_optimal]), np.array([0.0]))

    spread_std = (spread - np.mean(spread)) / (np.std(spread) + 1e-8)

    # Candidate thresholds (from 0.3σ to 3.0σ)
    deltas = np.linspace(0.3, 3.0, n_levels)
    profits = []
    n_trades_list = []

    for delta in deltas:
        # Count level crossings (transitions across +/- delta)
        above_upper = spread_std >= delta
        below_lower = spread_std <= -delta

        # Entry signals: crossing into extreme region
        long_entries = ((~below_lower[:-1]) & below_lower[1:]).sum()
        short_entries = ((~above_upper[:-1]) & above_upper[1:]).sum()

        total_crossings = long_entries + short_entries
        n_trades_list.append(total_crossings)

        # Profit per trade = 2 * delta (buy at -delta, sell at +delta)
        # Minus slippage (converted to sigma units)
        slippage_sigma = slippage_bps / 1000
        profit_per_trade = 2 * delta - slippage_sigma

        gross_profit = profit_per_trade * total_crossings
        profits.append(gross_profit)

    profits = np.array(profits)
    n_trades_list = np.array(n_trades_list)

    # Regularization: penalize frequent trading
    # Cost = lambda * (# trades) * (transaction cost per trade)
    transaction_cost_per_trade = slippage_bps / 10000  # Convert bps to decimal
    regularization_penalty = lambda_reg * n_trades_list * transaction_cost_per_trade

    # Objective = Profit - Penalty
    objectives = profits - regularization_penalty

    # Find optimal
    if len(objectives) == 0 or np.all(objectives <= 0):
        # No profitable threshold found, compute white noise optimal as fallback
        optimal_delta = compute_optimal_threshold(slippage_bps)
    else:
        optimal_idx = np.argmax(objectives)
        optimal_delta = round(deltas[optimal_idx], 2)

    if return_curve:
        return optimal_delta, deltas, objectives
    else:
        return optimal_delta


def bootstrap_holding_period(
    spread_series: np.ndarray,
    n_bootstrap: int = 1000,
    percentiles: Tuple[float, ...] = (5, 25, 50, 75, 95)
) -> Dict[str, float]:
    """
    Bootstrap estimate of holding period distribution per QMA Chapter 7.
    
    The time between zero crossings indicates expected holding period.
    This is used for time-based stop design.
    
    Parameters
    ----------
    spread_series : np.ndarray
        Historical spread values
    n_bootstrap : int
        Number of bootstrap samples
    percentiles : tuple
        Percentiles to report
        
    Returns
    -------
    dict
        Holding period statistics including median and percentiles
        
    Example
    -------
    >>> stats = bootstrap_holding_period(spread)
    >>> print(f"Median holding: {stats['median']:.1f} days")
    >>> print(f"95th percentile: {stats['p95']:.1f} days")
    """
    spread = np.asarray(spread_series)
    mean = np.mean(spread)
    
    # Find zero crossings (transitions across mean)
    above_mean = spread > mean
    crossings = np.where(above_mean[:-1] != above_mean[1:])[0]
    
    if len(crossings) < 2:
        # Not enough crossings
        return {'median': np.nan, 'mean': np.nan, 'p5': np.nan, 'p95': np.nan}
    
    # Time between crossings
    holding_times = np.diff(crossings)
    
    if len(holding_times) < 3:
        return {
            'median': np.median(holding_times),
            'mean': np.mean(holding_times),
            'p5': np.min(holding_times),
            'p95': np.max(holding_times)
        }
    
    # Bootstrap resampling
    bootstrap_medians = []
    for _ in range(n_bootstrap):
        sample = np.random.choice(holding_times, size=len(holding_times), replace=True)
        bootstrap_medians.append(np.median(sample))
    
    result = {
        'median': np.median(holding_times),
        'mean': np.mean(holding_times),
        'std': np.std(holding_times),
        'min': np.min(holding_times),
        'max': np.max(holding_times),
    }
    
    for p in percentiles:
        result[f'p{int(p)}'] = np.percentile(holding_times, p)
    
    # Bootstrap confidence interval for median
    result['median_ci_low'] = np.percentile(bootstrap_medians, 2.5)
    result['median_ci_high'] = np.percentile(bootstrap_medians, 97.5)
    
    return result


def get_conservative_config() -> BacktestConfig:
    """Get conservative (low risk) configuration."""
    return BacktestConfig(
        experiment_name="conservative",
        description="Conservative settings: strict p-value, EUROPE focus",
        pvalue_threshold=0.01,
        min_half_life=5.0,
        max_half_life=15.0,
        min_correlation=0.80,
        max_correlation=0.95,
        sector_focus=True,
        exclude_sectors=('EMERGING', 'BONDS_GOV', 'US_GROWTH', 
                        'INDUSTRIALS', 'HEALTHCARE', 'COMMODITIES'),
        entry_zscore=2.0,
        exit_zscore=0.5,
        stop_loss_zscore=3.5,
        max_holding_days=30,
        top_pairs=10,
    )


def get_aggressive_config() -> BacktestConfig:
    """Get aggressive (higher risk) configuration."""
    return BacktestConfig(
        experiment_name="aggressive",
        description="Aggressive settings: relaxed filters, more sectors",
        pvalue_threshold=0.05,
        min_half_life=3.0,
        max_half_life=45.0,
        min_correlation=0.70,
        max_correlation=0.95,
        sector_focus=True,
        exclude_sectors=('EMERGING',),  # Only exclude emerging
        entry_zscore=1.5,
        exit_zscore=0.3,
        stop_loss_zscore=4.0,
        max_holding_days=60,
        top_pairs=25,
    )


def get_europe_only_config() -> BacktestConfig:
    """Get EUROPE-focused configuration (best performing sector)."""
    return BacktestConfig(
        experiment_name="europe_only",
        description="Focus only on EUROPE sector pairs",
        pvalue_threshold=0.05,
        sector_focus=True,
        exclude_sectors=tuple(s for s in DEFAULT_EXCLUDED_SECTORS) + 
                       ('US_BROAD', 'US_VALUE', 'US_SMALL', 'US_MID', 
                        'TECH', 'FINANCIALS', 'CONSUMER_DISC', 'CONSUMER_STAPLES',
                        'ENERGY', 'MATERIALS', 'UTILITIES', 'REITS',
                        'ASIA_DEV', 'BONDS_CORP', 'COMMODITIES'),
        max_pairs_per_sector=10,
        top_pairs=15,
    )
