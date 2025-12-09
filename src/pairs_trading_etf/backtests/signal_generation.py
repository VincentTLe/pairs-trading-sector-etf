"""
Signal generation and position sizing for pairs trading.

This module handles:
- Z-score calculation and signal generation
- Time-based stop loss logic (Vidyamurthy Ch.8)
- VIX regime filtering
- Volatility-adjusted position sizing
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from ..constants import (
    MIN_STOP_LOSS_FLOOR,
    DEFAULT_ENTRY_THRESHOLD_SIGMA,
    VIX_THRESHOLD,
    VIX_LOOKBACK_DAYS,
    VIX_MIN_SCALE,
    VIX_MAX_SCALE,
    ADAPTIVE_LOOKBACK_MULTIPLIER,
    ADAPTIVE_LOOKBACK_MIN,
    ADAPTIVE_LOOKBACK_MAX,
    DEFAULT_EXIT_THRESHOLD_SIGMA,
    EXIT_TOLERANCE_SIGMA,
    DEFAULT_STOP_LOSS_SIGMA,
    STOP_TIGHTENING_RATE,
)

logger = logging.getLogger(__name__)


# =============================================================================
# TIME-BASED STOP LOSS (VIDYAMURTHY CH.8)
# =============================================================================

def calculate_time_based_stop(
    entry_z: float,
    current_z: float,
    holding_days: int,
    half_life: float,
    base_stop_zscore: float,
    tightening_rate: float = STOP_TIGHTENING_RATE,
) -> Tuple[bool, float]:
    """
    Time-based stop tightening per Vidyamurthy insight.

    "The mere passage of time represents an increase in risk"

    As holding period exceeds half-life, the stop loss tightens,
    because the probability of mean reversion decreases.

    Parameters
    ----------
    entry_z : float
        Z-score at entry
    current_z : float
        Current z-score
    holding_days : int
        Days held
    half_life : float
        Expected half-life
    base_stop_zscore : float
        Base stop-loss threshold
    tightening_rate : float
        Rate of stop tightening per half-life elapsed

    Returns
    -------
    tuple
        (should_stop, effective_stop_zscore)
    """
    # Calculate how many half-lives have passed
    half_lives_passed = holding_days / max(half_life, 1)

    # Only start tightening after 1 full half-life has passed
    if half_lives_passed < 1.0:
        return False, base_stop_zscore

    # Tighten stop as more half-lives pass (starts after 1 HL)
    # After 1 HL: start tightening
    # After 2 HL: stop tightens by tightening_rate
    excess_hl = half_lives_passed - 1.0
    tightening = excess_hl * tightening_rate * base_stop_zscore

    # Effective stop gets closer to entry z
    effective_stop = base_stop_zscore - tightening
    effective_stop = max(effective_stop, MIN_STOP_LOSS_FLOOR)  # Floor (prevents overly aggressive tightening)

    # Check if stop triggered - the position is getting WORSE (diverging)
    # For long spread (entered at negative z): stop if z goes MORE negative
    # For short spread (entered at positive z): stop if z goes MORE positive
    direction = np.sign(entry_z)  # -1 for long spread, +1 for short spread

    if direction < 0:  # Long spread (entered at negative z)
        # Stop if z is MORE negative than effective_stop (diverging)
        should_stop = current_z <= -effective_stop
    else:  # Short spread (entered at positive z)
        # Stop if z is MORE positive than effective_stop (diverging)
        should_stop = current_z >= effective_stop

    return should_stop, effective_stop


# =============================================================================
# VIX REGIME FILTER
# =============================================================================

def check_vix_regime(
    vix_data: Optional[pd.Series],
    current_date: pd.Timestamp,
    vix_threshold: float = VIX_THRESHOLD,
    lookback_days: int = VIX_LOOKBACK_DAYS,
) -> Dict[str, Any]:
    """
    Check if current market regime is high volatility based on VIX.

    Parameters
    ----------
    vix_data : pd.Series or None
        VIX closing prices indexed by date
    current_date : pd.Timestamp
        Current trading date
    vix_threshold : float
        VIX level above which to flag high volatility regime
    lookback_days : int
        Number of days to average VIX over

    Returns
    -------
    dict
        Contains: is_high_vol, current_vix, avg_vix
    """
    if vix_data is None or len(vix_data) == 0:
        return {
            'is_high_vol': False,
            'current_vix': None,
            'avg_vix': None,
        }

    try:
        # Get VIX data up to current date
        available = vix_data[vix_data.index <= current_date]

        if len(available) == 0:
            return {'is_high_vol': False, 'current_vix': None, 'avg_vix': None}

        current_vix = available.iloc[-1]
        avg_vix = available.iloc[-lookback_days:].mean() if len(available) >= lookback_days else available.mean()

        is_high_vol = current_vix > vix_threshold or avg_vix > vix_threshold

        return {
            'is_high_vol': is_high_vol,
            'current_vix': float(current_vix),
            'avg_vix': float(avg_vix),
        }
    except Exception as e:
        logger.debug(f"VIX check failed: {e}")
        return {'is_high_vol': False, 'current_vix': None, 'avg_vix': None}


# =============================================================================
# VOLATILITY-ADJUSTED POSITION SIZING
# =============================================================================

def calculate_volatility_adjusted_size(
    base_capital: float,
    spread_volatility: float,
    target_volatility: float = 0.02,
    min_scale: float = VIX_MIN_SCALE,
    max_scale: float = VIX_MAX_SCALE,
) -> float:
    """
    Calculate position size adjusted for spread volatility.

    Position is scaled inversely to volatility:
    - High volatility spread -> smaller position
    - Low volatility spread -> larger position

    Parameters
    ----------
    base_capital : float
        Base capital allocation for this trade
    spread_volatility : float
        Daily volatility of the spread
    target_volatility : float
        Target daily volatility for position (default 2%)
    min_scale : float
        Minimum position size as fraction of base (0.25 = 25%)
    max_scale : float
        Maximum position size as fraction of base (2.0 = 200%)

    Returns
    -------
    float
        Volatility-adjusted position size
    """
    if spread_volatility <= 0 or np.isnan(spread_volatility):
        return base_capital

    # Scale factor: target_vol / actual_vol
    scale = target_volatility / spread_volatility

    # Clamp to min/max
    scale = max(min_scale, min(max_scale, scale))

    return base_capital * scale


# =============================================================================
# Z-SCORE CALCULATION UTILITIES
# =============================================================================

def calculate_rolling_zscore(
    spread: pd.Series,
    lookback: int = 60,
    min_periods: int = 30,
) -> pd.Series:
    """
    Calculate rolling z-score for a spread series.

    Parameters
    ----------
    spread : pd.Series
        Spread time series
    lookback : int
        Rolling window size
    min_periods : int
        Minimum periods for calculation

    Returns
    -------
    pd.Series
        Rolling z-score series
    """
    rolling_mean = spread.rolling(window=lookback, min_periods=min_periods).mean()
    rolling_std = spread.rolling(window=lookback, min_periods=min_periods).std()

    # Avoid division by zero
    zscore = (spread - rolling_mean) / rolling_std.where(rolling_std > 0, np.nan)

    return zscore


def calculate_adaptive_lookback(
    half_life: float,
    multiplier: float = ADAPTIVE_LOOKBACK_MULTIPLIER,
    min_lookback: int = ADAPTIVE_LOOKBACK_MIN,
    max_lookback: int = ADAPTIVE_LOOKBACK_MAX,
) -> int:
    """
    Calculate adaptive lookback window based on half-life.

    Pairs with faster mean-reversion (shorter half-life) use shorter lookbacks.
    Pairs with slower mean-reversion (longer half-life) use longer lookbacks.

    Parameters
    ----------
    half_life : float
        Half-life of the spread in days
    multiplier : float
        Multiplier for half-life to get lookback
    min_lookback : int
        Minimum lookback period
    max_lookback : int
        Maximum lookback period

    Returns
    -------
    int
        Adaptive lookback window size
    """
    lookback = int(multiplier * half_life)
    return max(min_lookback, min(max_lookback, lookback))


def generate_entry_signals(
    zscore: pd.Series,
    entry_threshold: float = DEFAULT_ENTRY_THRESHOLD_SIGMA,
) -> pd.DataFrame:
    """
    Generate entry signals from z-score series.

    Parameters
    ----------
    zscore : pd.Series
        Z-score time series
    entry_threshold : float
        Z-score threshold for entry

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: signal (1=long spread, -1=short spread, 0=no signal)
    """
    signals = pd.DataFrame(index=zscore.index)

    # Long spread when z < -threshold (spread is below mean)
    # Short spread when z > +threshold (spread is above mean)
    signals['signal'] = 0
    signals.loc[zscore <= -entry_threshold, 'signal'] = 1   # Long spread
    signals.loc[zscore >= entry_threshold, 'signal'] = -1   # Short spread
    signals['zscore'] = zscore

    return signals


def check_exit_conditions(
    current_z: float,
    entry_z: float,
    direction: int,
    holding_days: int,
    half_life: float,
    exit_threshold: float = DEFAULT_EXIT_THRESHOLD_SIGMA,
    exit_tolerance: float = EXIT_TOLERANCE_SIGMA,
    stop_loss_sigma: float = DEFAULT_STOP_LOSS_SIGMA,
    use_time_stops: bool = True,
    tightening_rate: float = STOP_TIGHTENING_RATE,
) -> Tuple[bool, str]:
    """
    Check if position should be exited.

    Parameters
    ----------
    current_z : float
        Current z-score
    entry_z : float
        Z-score at entry
    direction : int
        Position direction (1=long spread, -1=short spread)
    holding_days : int
        Days held
    half_life : float
        Half-life of the spread
    exit_threshold : float
        Z-score threshold for exit (mean reversion target)
    exit_tolerance : float
        Tolerance band around exit threshold
    stop_loss_sigma : float
        Stop-loss z-score threshold
    use_time_stops : bool
        Whether to use time-based stop tightening
    tightening_rate : float
        Rate of stop tightening per half-life

    Returns
    -------
    tuple
        (should_exit, exit_reason)
    """
    should_exit = False
    exit_reason = None

    if direction == 1:  # Long spread
        # Exit if z >= -(exit_threshold + tolerance) i.e. within tolerance of mean
        if current_z >= -(exit_threshold + exit_tolerance):
            should_exit = True
            exit_reason = "convergence"
        else:
            # Check stop loss with optional time-based tightening
            if use_time_stops:
                time_stop, effective_stop = calculate_time_based_stop(
                    entry_z, current_z, holding_days, half_life,
                    stop_loss_sigma, tightening_rate
                )
                if time_stop:
                    should_exit = True
                    exit_reason = "stop_loss_time"
            else:
                if current_z <= -stop_loss_sigma:
                    should_exit = True
                    exit_reason = "stop_loss"
    else:  # Short spread
        # Exit if z <= (exit_threshold + tolerance) i.e. within tolerance of mean
        if current_z <= (exit_threshold + exit_tolerance):
            should_exit = True
            exit_reason = "convergence"
        else:
            # Check stop loss with optional time-based tightening
            if use_time_stops:
                time_stop, effective_stop = calculate_time_based_stop(
                    entry_z, current_z, holding_days, half_life,
                    stop_loss_sigma, tightening_rate
                )
                if time_stop:
                    should_exit = True
                    exit_reason = "stop_loss_time"
            else:
                if current_z >= stop_loss_sigma:
                    should_exit = True
                    exit_reason = "stop_loss"

    return should_exit, exit_reason
