"""
Pair selection and cointegration testing for pairs trading.

This module provides:
- Cointegration testing (Engle-Granger)
- Pair selection with sector diversification
- Cointegration drift monitoring
- Vidyamurthy metrics (SNR, Zero-Crossing Rate)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Optional, Dict, List, Any, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import coint

from .config import BacktestConfig
from ..utils.sectors import get_sector, are_same_sector
from ..constants import (
    TRADING_DAYS_PER_YEAR,
    MIN_OBSERVATIONS_FOR_STATS,
    DEFAULT_MIN_HALF_LIFE,
    DEFAULT_MAX_HALF_LIFE,
    THRESHOLD_DISAGREEMENT_TOLERANCE,
    PVALUE_FORMATION,
    DRIFT_PVALUE_THRESHOLD,
)

logger = logging.getLogger(__name__)


# =============================================================================
# VIDYAMURTHY FRAMEWORK - SNR & TRADABILITY METRICS
# =============================================================================

def calculate_snr(spread: pd.Series, half_life: float) -> float:
    """
    Calculate Signal-to-Noise Ratio (SNR) per Vidyamurthy Ch.6.

    SNR = sigma_stationary / sigma_nonstationary

    For a mean-reverting spread:
    - sigma_stationary = standard deviation of the spread
    - sigma_nonstationary = standard deviation of innovations (changes)

    Higher SNR indicates stronger cointegration (mean-reverting vs noise).

    Parameters
    ----------
    spread : pd.Series
        Cointegration spread (residuals)
    half_life : float
        Half-life in days

    Returns
    -------
    float
        SNR ratio (typically want SNR >= 2.0)
    """
    if len(spread) < MIN_OBSERVATIONS_FOR_STATS:
        return 0.0

    # Standard deviation of spread (stationary component)
    sigma_stationary = spread.std()

    # Standard deviation of changes (non-stationary/noise component)
    spread_diff = spread.diff().dropna()
    sigma_noise = spread_diff.std()

    if sigma_noise == 0 or np.isnan(sigma_noise):
        return 0.0

    snr = sigma_stationary / sigma_noise
    return float(snr)


def calculate_zero_crossing_rate(spread: pd.Series, lookback: int = 252) -> Tuple[float, float]:
    """
    Calculate Zero-Crossing Rate per Vidyamurthy Ch.7.

    The zero-crossing rate measures how frequently the spread crosses
    its equilibrium (mean). Higher rate = more tradeable.

    Also calculates expected holding period:
    E[holding_period] =~ trading_days / (2 * zero_crossings)

    Parameters
    ----------
    spread : pd.Series
        Cointegration spread
    lookback : int
        Period for calculation (default 252 = 1 year)

    Returns
    -------
    tuple
        (zero_crossing_rate_per_year, expected_holding_days)
    """
    if len(spread) < MIN_OBSERVATIONS_FOR_STATS:
        return 0.0, float('inf')

    # Use last N days
    s = spread.iloc[-lookback:] if len(spread) > lookback else spread

    # Demean the spread
    demeaned = s - s.mean()

    # Count zero crossings
    signs = np.sign(demeaned.values)
    signs[signs == 0] = 1  # Treat exactly 0 as positive

    crossings = np.sum(signs[1:] != signs[:-1])

    # Annualize
    n_days = len(s)
    zcr_annual = crossings * (TRADING_DAYS_PER_YEAR / n_days)

    # Expected holding period (time between entries and exits)
    # Vidyamurthy: E[T] ~= N / (2 * crossings) where N is number of observations
    if crossings > 0:
        expected_holding = n_days / (2.0 * crossings)
    else:
        expected_holding = float('inf')

    return float(zcr_annual), float(expected_holding)


def calculate_factor_correlation(series_x: pd.Series, series_y: pd.Series) -> float:
    """
    Calculate common factor correlation per Vidyamurthy APT model.

    High correlation between price series indicates they share
    common factor exposure (good for pairs trading).

    Parameters
    ----------
    series_x : pd.Series
        First price series
    series_y : pd.Series
        Second price series

    Returns
    -------
    float
        Correlation coefficient (want >= 0.85)
    """
    aligned = pd.concat([series_x, series_y], axis=1, join='inner').dropna()
    if len(aligned) < MIN_OBSERVATIONS_FOR_STATS:
        return 0.0

    # Use log returns for correlation
    returns_x = np.log(aligned.iloc[:, 0]).diff().dropna()
    returns_y = np.log(aligned.iloc[:, 1]).diff().dropna()

    corr = returns_x.corr(returns_y)
    return float(corr) if not np.isnan(corr) else 0.0


# =============================================================================
# COINTEGRATION TESTING
# =============================================================================

def run_engle_granger_test(
    series_x: pd.Series,
    series_y: pd.Series,
    use_log: bool = True,
    pvalue_threshold: float = PVALUE_FORMATION,
    min_half_life: float = DEFAULT_MIN_HALF_LIFE,
    max_half_life: float = DEFAULT_MAX_HALF_LIFE,
) -> Optional[Dict[str, float]]:
    """
    Run Engle-Granger cointegration test on two price series.

    Uses statsmodels.coint() which implements proper MacKinnon critical values
    for cointegration (NOT standard ADF critical values).

    Parameters
    ----------
    series_x : pd.Series
        First price series
    series_y : pd.Series
        Second price series
    use_log : bool
        Whether to use log prices (recommended)
    pvalue_threshold : float
        Maximum p-value for cointegration
    min_half_life : float
        Minimum half-life in days
    max_half_life : float
        Maximum half-life in days

    Returns
    -------
    dict or None
        Dictionary with hedge_ratio, pvalue, half_life, spread stats
        None if pair doesn't pass cointegration test
    """
    try:
        # Align series
        aligned = pd.concat([series_x, series_y], axis=1, join='inner').dropna()
        if len(aligned) < 60:
            return None

        x = aligned.iloc[:, 0]
        y = aligned.iloc[:, 1]

        if use_log:
            x = np.log(x)
            y = np.log(y)

        # Engle-Granger test using statsmodels
        test_stat, pvalue, crit_values = coint(x, y, trend='c', maxlag=1, autolag='aic')

        if pvalue > pvalue_threshold:
            return None

        # Calculate hedge ratio via OLS
        slope, intercept, r_value, _, std_err = stats.linregress(y, x)
        hedge_ratio = slope

        # Calculate spread
        spread = x - (intercept + hedge_ratio * y)

        # Estimate half-life using OU model
        spread_lag = spread.shift(1).dropna()
        spread_diff = spread.diff().dropna()

        common_idx = spread_lag.index.intersection(spread_diff.index)
        spread_lag = spread_lag.loc[common_idx]
        spread_diff = spread_diff.loc[common_idx]

        if len(spread_lag) < 30:
            return None

        slope_hl, _, _, _, _ = stats.linregress(spread_lag, spread_diff)

        if slope_hl >= 0:
            return None

        phi = 1 + slope_hl
        if phi <= 0 or phi >= 1:
            return None

        half_life = -np.log(2) / np.log(phi)

        if not (min_half_life <= half_life <= max_half_life):
            return None

        # Spread statistics
        spread_std = spread.std()
        spread_range = spread.max() - spread.min()

        # Vidyamurthy metrics
        snr = calculate_snr(spread, half_life)
        zcr, expected_holding = calculate_zero_crossing_rate(spread)

        return {
            'hedge_ratio': float(hedge_ratio),
            'intercept': float(intercept),
            'pvalue': float(pvalue),
            'test_stat': float(test_stat),
            'half_life': float(half_life),
            'spread_mean': float(spread.mean()),
            'spread_std': float(spread_std),
            'spread_range': float(spread_range),
            'r_squared': float(r_value ** 2),
            # Vidyamurthy metrics
            'snr': float(snr),
            'zero_crossing_rate': float(zcr),
            'expected_holding': float(expected_holding),
        }

    except Exception as e:
        logger.debug(f"Cointegration test failed: {e}")
        return None


def monitor_cointegration_drift(
    prices: pd.DataFrame,
    pair: Tuple[str, str],
    lookback_days: int = 60,
    pvalue_threshold: float = DRIFT_PVALUE_THRESHOLD,
    min_observations: int = 30,
    use_log: bool = True,
) -> Dict[str, Any]:
    """
    Monitor cointegration drift during trading period.

    CRITICAL FIX for Bug #1: Cointegration can break during trading!

    This function re-tests cointegration on a rolling window of recent data.
    If p-value exceeds threshold, the pair relationship has broken and
    position should be exited.

    Usage:
    ------
    Call this monthly (every 21 trading days) during trading period:

    >>> if days_in_trade % 21 == 0:
    >>>     drift_status = monitor_cointegration_drift(prices, pair)
    >>>     if drift_status['drift_detected']:
    >>>         # Exit position - cointegration broken!
    >>>         exit_reason = 'cointegration_drift'

    Parameters
    ----------
    prices : pd.DataFrame
        Recent price data (should include at least lookback_days)
    pair : tuple
        (ticker_x, ticker_y) pair to monitor
    lookback_days : int
        Rolling window for re-testing (default: 60 days)
    pvalue_threshold : float
        Maximum acceptable p-value (default: 0.15, looser than formation 0.05)
    min_observations : int
        Minimum observations required for valid test
    use_log : bool
        Whether to use log prices

    Returns
    -------
    dict
        {
            'drift_detected': bool,        # True if cointegration broken
            'pvalue': float,               # Current p-value
            'pvalue_change': float,        # Change from formation (if available)
            'hedge_ratio': float,          # Current hedge ratio
            'half_life': float,            # Current half-life
            'observations': int,           # Number of observations used
            'test_valid': bool,            # Whether test had enough data
            'reason': str,                 # Reason for drift detection
        }

    Academic References
    -------------------
    - Gregory et al. (2011): "Monitoring cointegration breakdowns essential"
    - Nath (2003): "Cointegration relationships not static over time"
    - Vidyamurthy (2004): Suggests periodic re-estimation of parameters
    """
    leg_x, leg_y = pair

    result = {
        'drift_detected': False,
        'pvalue': None,
        'pvalue_change': None,
        'hedge_ratio': None,
        'half_life': None,
        'observations': 0,
        'test_valid': False,
        'reason': '',
    }

    try:
        # Check if we have enough data
        if len(prices) < min_observations:
            result['reason'] = f'insufficient_data: {len(prices)} < {min_observations}'
            return result

        # Get recent window
        window = prices.iloc[-lookback_days:] if len(prices) >= lookback_days else prices

        if leg_x not in window.columns or leg_y not in window.columns:
            result['reason'] = 'missing_tickers'
            return result

        x = window[leg_x].dropna()
        y = window[leg_y].dropna()

        # Align series
        aligned = pd.concat([x, y], axis=1, join='inner').dropna()
        result['observations'] = len(aligned)

        if len(aligned) < min_observations:
            result['reason'] = f'insufficient_aligned: {len(aligned)} < {min_observations}'
            return result

        result['test_valid'] = True

        x = aligned.iloc[:, 0]
        y = aligned.iloc[:, 1]

        if use_log:
            x = np.log(x)
            y = np.log(y)

        # Run Engle-Granger test
        test_stat, pvalue, crit_values = coint(x, y, trend='c', maxlag=1, autolag='aic')

        result['pvalue'] = float(pvalue)

        # Calculate current hedge ratio
        slope, intercept, _, _, _ = stats.linregress(y, x)
        result['hedge_ratio'] = float(slope)

        # Calculate spread and half-life
        spread = x - (intercept + slope * y)

        # Estimate half-life
        spread_lag = spread.shift(1).dropna()
        spread_diff = spread.diff().dropna()

        common_idx = spread_lag.index.intersection(spread_diff.index)
        if len(common_idx) >= 20:
            spread_lag = spread_lag.loc[common_idx]
            spread_diff = spread_diff.loc[common_idx]

            slope_hl, _, _, _, _ = stats.linregress(spread_lag, spread_diff)

            if slope_hl < 0:
                phi = 1 + slope_hl
                if 0 < phi < 1:
                    half_life = -np.log(2) / np.log(phi)
                    result['half_life'] = float(half_life)

        # Check if drift detected
        if pvalue > pvalue_threshold:
            result['drift_detected'] = True
            result['reason'] = f'pvalue_exceeded: {pvalue:.4f} > {pvalue_threshold}'
        else:
            result['reason'] = f'ok: {pvalue:.4f} <= {pvalue_threshold}'

        return result

    except Exception as e:
        logger.debug(f"Cointegration drift monitoring failed: {e}")
        result['reason'] = f'error: {str(e)}'
        return result


def update_hedge_ratio(
    prices: pd.DataFrame,
    pair: Tuple[str, str],
    lookback: int = 63,
    use_log: bool = True,
) -> Tuple[float, float]:
    """
    Update hedge ratio using recent price data.

    Parameters
    ----------
    prices : pd.DataFrame
        Price data
    pair : tuple
        (ticker_x, ticker_y) pair
    lookback : int
        Days of data to use
    use_log : bool
        Whether to use log prices

    Returns
    -------
    tuple
        (hedge_ratio, intercept)
    """
    leg_x, leg_y = pair

    x = prices[leg_x].iloc[-lookback:]
    y = prices[leg_y].iloc[-lookback:]

    if use_log:
        x = np.log(x)
        y = np.log(y)

    slope, intercept, _, _, _ = stats.linregress(y, x)
    return slope, intercept


# =============================================================================
# PAIR SELECTION
# =============================================================================

def select_pairs(
    prices: pd.DataFrame,
    cfg: BacktestConfig,
    blacklist: Optional[set] = None,
) -> Tuple[List[Tuple[str, str]], Dict, Dict, Dict, Dict]:
    """
    Select cointegrated pairs from price data.

    Process:
    1. Filter by correlation
    2. Filter by sector (if sector_focus enabled)
    3. Test for cointegration
    4. Validate pair stability (if enabled)
    5. Score and rank pairs
    6. Apply diversification limits

    Parameters
    ----------
    prices : pd.DataFrame
        Price data with tickers as columns
    cfg : BacktestConfig
        Configuration object
    blacklist : set, optional
        Pairs to exclude

    Returns
    -------
    tuple
        (selected_pairs, hedge_ratios, half_lives, formation_stats, optimal_deltas)
        - selected_pairs: List of (ticker1, ticker2) tuples
        - hedge_ratios: Dict mapping pair -> hedge ratio
        - half_lives: Dict mapping pair -> half-life (days)
        - formation_stats: Dict mapping pair -> (mean, std) of spread
        - optimal_deltas: Dict mapping pair -> optimal entry threshold (sigma)
    """
    tickers = list(prices.columns)
    n_tickers = len(tickers)
    logger.info(f"Selecting pairs from {n_tickers} tickers")

    # Import validation functions if available
    try:
        from .validation import check_rolling_consistency
        validation_available = True
    except ImportError:
        validation_available = False
        logger.debug("Validation module not available")

    # Step 1: Correlation filter
    returns = prices.pct_change().dropna()
    corr_matrix = returns.corr()

    candidate_pairs = []
    for i in range(n_tickers):
        for j in range(i + 1, n_tickers):
            corr = corr_matrix.iloc[i, j]
            if cfg.min_correlation <= corr <= cfg.max_correlation:
                # Sector filter
                if cfg.sector_focus:
                    if are_same_sector(tickers[i], tickers[j]):
                        sector = get_sector(tickers[i])
                        if sector not in cfg.exclude_sectors:
                            candidate_pairs.append((tickers[i], tickers[j]))
                else:
                    candidate_pairs.append((tickers[i], tickers[j]))

    logger.info(f"Pairs with corr {cfg.min_correlation:.2f}-{cfg.max_correlation:.2f}: {len(candidate_pairs)}")

    # Blacklist filter
    if blacklist:
        before = len(candidate_pairs)
        candidate_pairs = [
            p for p in candidate_pairs
            if p not in blacklist and (p[1], p[0]) not in blacklist
        ]
        logger.info(f"After blacklist: {len(candidate_pairs)} (removed {before - len(candidate_pairs)})")

    # Step 2: Cointegration test
    cointegrated = []
    results = {}
    validation_scores = {}  # Store stability scores for ranking

    for pair in candidate_pairs:
        leg_x, leg_y = pair
        result = run_engle_granger_test(
            prices[leg_x],
            prices[leg_y],
            use_log=cfg.use_log_prices,
            pvalue_threshold=cfg.pvalue_threshold,
            min_half_life=cfg.min_half_life,
            max_half_life=cfg.max_half_life,
        )

        if result is not None:
            if result['spread_range'] >= cfg.min_spread_range_pct:
                # Hedge ratio filter - avoid imbalanced positions
                hr = abs(result['hedge_ratio'])
                if cfg.min_hedge_ratio <= hr <= cfg.max_hedge_ratio:
                    # Vidyamurthy filters: SNR and Zero-Crossing Rate
                    snr_ok = result.get('snr', 0) >= getattr(cfg, 'min_snr', 0)
                    zcr_ok = result.get('zero_crossing_rate', 0) >= getattr(cfg, 'min_zero_crossing_rate', 0)

                    if snr_ok and zcr_ok:
                        cointegrated.append(pair)
                        results[pair] = result
                        validation_scores[pair] = 1.0  # Default score

    logger.info(f"Cointegrated pairs: {len(cointegrated)}")

    if not cointegrated:
        return [], {}, {}, {}, {}

    # Step 2.5: Rolling consistency validation (if enabled)
    if validation_available and getattr(cfg, 'rolling_consistency', False):
        n_windows = getattr(cfg, 'n_rolling_windows', 4)
        min_passing = getattr(cfg, 'min_passing_windows', 2)

        logger.info(f"Running rolling consistency check ({n_windows} windows, {min_passing} required)")
        validated_pairs = []

        for pair in cointegrated:
            rc_result = check_rolling_consistency(
                prices=prices,
                pair=pair,
                use_log=cfg.use_log_prices,
                pvalue_threshold=cfg.pvalue_threshold,
                min_half_life=cfg.min_half_life,
                max_half_life=cfg.max_half_life,
                n_windows=n_windows,
                min_passing=min_passing,
            )

            if rc_result.get('passes', False):
                validated_pairs.append(pair)
                # Update validation score for ranking
                validation_scores[pair] = rc_result.get('score', 1.0)
                logger.debug(f"  {pair}: PASSED ({rc_result['passing_windows']}/{n_windows} windows)")
            else:
                logger.debug(f"  {pair}: FAILED ({rc_result.get('passing_windows', 0)}/{n_windows} windows)")

        removed = len(cointegrated) - len(validated_pairs)
        logger.info(f"After rolling consistency: {len(validated_pairs)} pairs (removed {removed})")
        cointegrated = validated_pairs

    if not cointegrated:
        logger.warning("No pairs passed rolling consistency check")
        return [], {}, {}, {}, {}

    # Step 3: Scoring - include Vidyamurthy metrics and validation scores
    scores = {}
    for pair in cointegrated:
        r = results[pair]
        pvalue_score = min(-np.log(max(r['pvalue'], 1e-10)) / 7.0, 1.0)
        hl_score = max(0, 1 - abs(r['half_life'] - 15) / 15)
        range_score = min(r['spread_range'] / 0.10, 1.0)

        # Hedge ratio quality score
        hr = abs(r['hedge_ratio'])
        hr_score = 1.0 - abs(hr - 1.0) / 1.0
        hr_score = max(0, min(1, hr_score))

        # Vidyamurthy metrics in scoring
        snr = r.get('snr', 1.0)
        zcr = r.get('zero_crossing_rate', 0)
        snr_score = min(snr / 3.0, 1.0)  # Normalize to ~3.0 max
        zcr_score = min(zcr / 20.0, 1.0)  # Normalize to ~20 crossings/year

        # Validation/stability score
        stability_score = validation_scores.get(pair, 1.0)

        # Updated weights to include Vidyamurthy metrics and stability
        scores[pair] = (
            0.20 * pvalue_score +
            0.15 * hl_score +
            0.10 * range_score +
            0.10 * hr_score +
            0.15 * snr_score +
            0.15 * zcr_score +
            0.15 * stability_score  # Stability matters!
        )

    sorted_pairs = sorted(cointegrated, key=lambda p: scores[p], reverse=True)

    # Step 4: Diversification (skip limits if unlimited_pairs)
    selected = []
    sector_counts = defaultdict(int)
    etf_counts = defaultdict(int)

    for pair in sorted_pairs:
        # Check pair limit (unless unlimited)
        if not cfg.unlimited_pairs and len(selected) >= cfg.top_pairs:
            break

        leg_x, leg_y = pair
        sector = get_sector(leg_x)

        # Apply diversification limits only if not unlimited
        if not cfg.unlimited_pairs:
            if sector_counts[sector] >= cfg.max_pairs_per_sector:
                continue
            if etf_counts[leg_x] >= cfg.max_pairs_per_etf or etf_counts[leg_y] >= cfg.max_pairs_per_etf:
                continue

        selected.append(pair)
        sector_counts[sector] += 1
        etf_counts[leg_x] += 1
        etf_counts[leg_y] += 1

    logger.info(f"Selected {len(selected)} pairs")

    # Log top pairs
    for i, pair in enumerate(selected[:5], 1):
        r = results[pair]
        sector = get_sector(pair[0])
        logger.info(f"  {i}. {pair} [{sector}]: p={r['pvalue']:.4f}, HL={r['half_life']:.1f}, range={r['spread_range']:.3f}")

    # Build output
    hedge_ratios = {p: results[p]['hedge_ratio'] for p in selected}
    half_lives = {p: results[p]['half_life'] for p in selected}
    formation_stats = {p: (results[p]['spread_mean'], results[p]['spread_std']) for p in selected}

    # Compute optimal thresholds per pair (Vidyamurthy Ch.8)
    optimal_deltas = {}
    if cfg.use_optimal_entry_threshold:
        from .config import compute_optimal_threshold, compute_nonparametric_threshold

        logger.info("Computing optimal entry thresholds per pair (Ch.8)...")

        for pair in selected:
            leg_x, leg_y = pair
            hr = hedge_ratios[pair]

            # Get formation spread
            if cfg.use_log_prices:
                spread = np.log(prices[leg_x]) - hr * np.log(prices[leg_y])
            else:
                spread = prices[leg_x] - hr * prices[leg_y]

            spread = spread.dropna().values

            # Compute optimal threshold
            method = cfg.optimal_threshold_method

            if method == 'white_noise':
                # Theoretical white noise optimal
                delta_opt = compute_optimal_threshold(slippage_bps=cfg.transaction_cost_bps)

            elif method == 'nonparametric':
                # Nonparametric from historical data
                delta_opt = compute_nonparametric_threshold(
                    spread,
                    slippage_bps=cfg.transaction_cost_bps,
                    lambda_reg=cfg.optimal_threshold_lambda
                )

            elif method == 'both':
                # Compute both and pick better one
                delta_white = compute_optimal_threshold(slippage_bps=cfg.transaction_cost_bps)
                delta_nonparam = compute_nonparametric_threshold(
                    spread,
                    slippage_bps=cfg.transaction_cost_bps,
                    lambda_reg=cfg.optimal_threshold_lambda
                )

                # Use nonparametric if significantly different
                if abs(delta_nonparam - delta_white) / delta_white > THRESHOLD_DISAGREEMENT_TOLERANCE:
                    delta_opt = delta_nonparam
                    logger.debug(f"  {pair}: Using nonparametric Δ={delta_opt:.2f} (white noise={delta_white:.2f})")
                else:
                    delta_opt = delta_white
                    logger.debug(f"  {pair}: Using white noise Δ={delta_opt:.2f}")

            else:
                # Fallback to white noise
                delta_opt = compute_optimal_threshold(slippage_bps=cfg.transaction_cost_bps)

            optimal_deltas[pair] = delta_opt

        logger.info(f"Optimal Δ range: [{min(optimal_deltas.values()):.2f}, {max(optimal_deltas.values()):.2f}]")
    else:
        # Use global threshold for all pairs
        for pair in selected:
            optimal_deltas[pair] = cfg.entry_threshold_sigma

    return selected, hedge_ratios, half_lives, formation_stats, optimal_deltas
