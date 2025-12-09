"""
Central Constants for Pairs Trading System
===========================================

All hardcoded parameters should reference constants defined here.
Each constant includes:
- Value
- Justification/source
- Context where used

Last updated: 2025-12-08 (Session 20 cleanup)
"""

# =============================================================================
# CALENDAR CONSTANTS
# =============================================================================

TRADING_DAYS_PER_YEAR = 252
"""
Number of trading days per year in US markets.
Source: Standard market practice (252-253 days accounting for holidays)
Used in: Annualization calculations, zero-crossing rate
"""

TRADING_DAYS_PER_MONTH = 21
"""
Approximate trading days per month (252 / 12 ≈ 21)
Source: Standard practice
Used in: Cointegration drift monitoring frequency
"""

# =============================================================================
# CORRELATION THRESHOLDS
# =============================================================================

DEFAULT_MIN_CORRELATION = 0.75
"""
Minimum correlation for pair candidates.
Source: Vidyamurthy (2004) Ch.6 - Pairs should share common factors
Rationale: Below 0.75, pairs lack sufficient co-movement
          Above 0.95, pairs too similar (risk duplication)
Used in: Pair selection, filtering
"""

DEFAULT_MAX_CORRELATION = 0.99
"""
Maximum correlation to avoid near-duplicate pairs.
Source: Practitioner knowledge
Rationale: Correlation > 0.99 suggests synthetic duplication
          (e.g., VTI and SPY are essentially same exposure)
Used in: Pair selection, filtering
"""

# Legacy values (DEPRECATED - found in old code)
LEGACY_MIN_CORR = 0.60  # TOO PERMISSIVE - DO NOT USE
LEGACY_MAX_CORR = 0.99  # TOO PERMISSIVE - DO NOT USE

# =============================================================================
# HALF-LIFE BOUNDS
# =============================================================================

DEFAULT_MIN_HALF_LIFE = 5.0
"""
Minimum half-life in days for mean reversion.
Source: Vidyamurthy (2004) Ch.7 "Testing for Tradability"
Rationale: HL < 5 days indicates noise rather than true mean reversion
          Too fast to trade profitably with transaction costs
Used in: Pair filtering, tradability assessment
"""

DEFAULT_MAX_HALF_LIFE = 30.0
"""
Maximum half-life in days.
Source: Vidyamurthy (2004) Ch.7
Rationale: HL > 30 days means capital tied up too long
          Mean reversion too slow for practical trading
Used in: Pair filtering, tradability assessment
"""


# =============================================================================
# LOOKBACK WINDOWS
# =============================================================================

FORMATION_PERIOD_DAYS = 180
"""
Formation period length (1 trading year).
Source: Gatev et al. (2006) - Standard 12-month formation
Rationale: Sufficient data for robust cointegration testing
          Balances stability vs adaptability
Used in: Pair selection, cointegration testing
"""

DEFAULT_ZSCORE_LOOKBACK = 60
"""
Default lookback for z-score calculation (when not using adaptive).
Source: QMA practice, López de Prado (2018)
Rationale: ~3 months balances responsiveness vs stability
          Roughly 4x typical half-life (15 days)
Used in: Z-score calculation, signal generation
"""

ADAPTIVE_LOOKBACK_MIN = 30
"""
Minimum adaptive lookback window.
Source: Statistical requirement
Rationale: Need at least 30 observations for stable mean/std estimates
          Below this, z-scores become noisy
Used in: Adaptive z-score calculation
"""

ADAPTIVE_LOOKBACK_MAX = 120
"""
Maximum adaptive lookback window.
Source: Empirical testing
Rationale: Beyond ~6 months, using stale spread characteristics
          Market regimes may have changed
Used in: Adaptive z-score calculation
"""

ADAPTIVE_LOOKBACK_MULTIPLIER = 4.0
"""
Lookback = multiplier × half-life for adaptive windows.
Source: QMA Level 2 methodology
Rationale: 4× half-life captures ~98% of mean reversion decay
          Balances current regime vs historical baseline
Used in: Adaptive z-score calculation
"""

ZCR_LOOKBACK_DAYS = 252
"""
Lookback for zero-crossing rate calculation.
Source: Vidyamurthy (2004) Ch.7
Rationale: Need full year to estimate annual crossing frequency
          Seasonal patterns may exist
Used in: Tradability filtering (zero-crossing rate)
"""

DRIFT_MONITOR_LOOKBACK = 60
"""
Lookback window for cointegration drift monitoring.
Source: Gregory et al. (2011) - structural break testing
Rationale: ~3 months balances detecting breaks vs false alarms
          Shorter = more sensitive but noisier
Used in: Cointegration drift re-testing during trading
"""

SPREAD_RANGE_LOOKBACK = 252
"""
Lookback for calculating spread range (1 year).
Source: Need full market cycle
Rationale: Captures seasonal patterns and full regime
Used in: Spread range % calculation
"""

SPREAD_RANGE_MIN_OBS = 126
"""
Minimum observations for valid spread range calculation.
Source: Statistical requirement
Rationale: Need at least 6 months (half year) of data
Used in: Spread range % calculation
"""

# =============================================================================
# MINIMUM OBSERVATIONS
# =============================================================================

MIN_OBSERVATIONS_FORMATION = 252
"""
Minimum observations required for pair formation.
Source: Econometric requirement for cointegration tests
Rationale: ADF test needs sufficient data for power
          252 days = 1 year, standard practice
Used in: Pair selection, data validation
"""

MIN_OBSERVATIONS_FOR_STATS = 30
"""
Minimum observations for statistical calculations (SNR, ZCR, correlation).
Source: Statistical rule of thumb (n ≥ 30 for CLT)
Rationale: Below 30, sample statistics unreliable
Used in: SNR, ZCR, factor correlation calculations
"""

MIN_OBSERVATIONS_DRIFT = 30
"""
Minimum observations for cointegration drift monitoring.
Source: Engle-Granger test power requirement
Rationale: Below 30, p-value estimates unstable
Used in: Monthly drift monitoring during trading
"""

# =============================================================================
# P-VALUE THRESHOLDS
# =============================================================================

PVALUE_FORMATION = 0.05
"""
P-value threshold for formation phase cointegration test.
Source: Engle-Granger (1987) - standard 5% significance
Rationale: 0.01 too strict (miss valid pairs), 0.10 too loose (noise)
          0.05 balances Type I and Type II errors
Used in: Pair selection, initial cointegration testing
"""

PVALUE_DRIFT = 0.15
"""
P-value threshold for drift monitoring (looser than formation).
Source: Gregory et al. (2011) - structural break testing
Rationale: During trading, we want to detect SIGNIFICANT drift only
          Too strict (0.05) causes premature exits
          0.15 allows temporary degradation but exits on structural break
Used in: Cointegration drift monitoring exit logic
"""

# =============================================================================
# ENTRY/EXIT THRESHOLDS
# =============================================================================

OPTIMAL_ENTRY_THRESHOLD_WHITENOISE = 0.75
"""
Optimal entry threshold for white noise spread (Vidyamurthy formula).
Source: Vidyamurthy (2004) Ch.8 p.119-120
Formula: Δ* = arg max [Δ × (1 - N(Δ)) × 2T]
Rationale: Maximizes profit function accounting for entry probability
          and holding time. NOT the traditional 2.0σ!
Used in: Optimal threshold calculation (white noise method)
"""

DEFAULT_ENTRY_THRESHOLD_SIGMA = 2.0
"""
Legacy/fallback entry threshold (2 standard deviations).
Source: Traditional pairs trading (Gatev et al. 2006)
Rationale: Statistical significance (95% confidence)
          Used when NOT using optimal threshold
Used in: Legacy signal generation, fallback
"""

DEFAULT_EXIT_THRESHOLD_SIGMA = 0.0
"""
Exit threshold (spread returns to mean).
Source: Mean reversion theory
Rationale: Exit when spread converges to equilibrium (z ≈ 0)
Used in: Exit signal generation
"""

EXIT_TOLERANCE_SIGMA = 0.1
"""
Tolerance band around exit threshold.
Source: Vidyamurthy (2004) Ch.8
Rationale: Allows exit if |z - exit_threshold| ≤ tolerance
          Prevents waiting for exact zero crossing
Used in: Exit condition checking
"""

DEFAULT_STOP_LOSS_SIGMA = 4.0
"""
Default stop-loss threshold (4 standard deviations).
Source: Practitioner knowledge (NOT academically justified)
Rationale: 4σ is ~0.006% probability if truly Gaussian
          Indicates fundamental relationship breakdown
          BUT: No clear academic source - may need tuning
Used in: Stop-loss exit logic
"""

MIN_STOP_LOSS_FLOOR = 1.5
"""
Minimum stop-loss floor for time-based tightening.
Source: Risk management practice
Rationale: Even with tightening, don't let stop go below 1.5σ
          Prevents premature exits on normal fluctuations
Used in: Time-based stop-loss tightening
"""

# =============================================================================
# VIX PARAMETERS
# =============================================================================

VIX_THRESHOLD = 30.0
"""
VIX level to halt new entries (high volatility regime).
Source: Market practice - VIX > 30 indicates fear/crisis
Rationale: Above 30, market regime changes
          Cointegration relationships may break down
Used in: Entry logic, position scaling
"""

VIX_LOOKBACK_DAYS = 5
"""
Days to average VIX over (smoothing).
Source: Practitioner knowledge
Rationale: Smooth out intraday VIX spikes
          5 days = 1 trading week
Used in: VIX-based position scaling
"""

VIX_MIN_SCALE = 0.25
"""
Minimum position size scale when VIX high.
Source: Risk management practice
Rationale: Reduce exposure 75% in high volatility
          Preserve capital, avoid drawdowns
Used in: VIX-based position sizing
"""

VIX_MAX_SCALE = 2.0
"""
Maximum position size scale when VIX low.
Source: Risk management practice
Rationale: Double exposure in calm markets
          Capitalize on favorable conditions
Used in: VIX-based position sizing
"""

# =============================================================================
# POSITION MANAGEMENT
# =============================================================================

DEFAULT_MAX_HOLDING_DAYS = 60
"""
Maximum holding period (fallback when not using dynamic).
Source: Practitioner knowledge (NOT well justified)
Rationale: ~3× typical half-life (20 days)
          Prevents capital tied up indefinitely
          BUT: Should be justified better or use dynamic holding
Used in: Time-based exit when dynamic_max_holding=False
"""

DEFAULT_MAX_HOLDING_MULTIPLIER = 3.0
"""
Dynamic max holding = multiplier × half-life.
Source: Mean reversion theory
Rationale: After 3× half-life, 87.5% of reversion should occur
          Beyond this, relationship may have broken
Used in: Dynamic maximum holding period
"""

DEFAULT_MAX_POSITIONS = 10
"""
Maximum concurrent positions.
Source: Vidyamurthy (2004) Ch.5 - "10-15 active positions"
Rationale: Diversification vs focus
          Too few = concentration risk
          Too many = capital fragmentation
Used in: Position limit checking
"""

# =============================================================================
# HEDGE RATIO BOUNDS
# =============================================================================

MIN_HEDGE_RATIO = 0.5
"""
Minimum absolute hedge ratio.
Source: Risk management
Rationale: |HR| < 0.5 means spread dominated by one leg
          Becomes directional bet, not pairs trade
Used in: Hedge ratio validation
"""

MAX_HEDGE_RATIO = 2.0
"""
Maximum absolute hedge ratio.
Source: Risk management
Rationale: |HR| > 2.0 indicates unstable relationship
          Over-hedging one leg
Used in: Hedge ratio validation
"""

# =============================================================================
# BLACKLIST PARAMETERS
# =============================================================================

BLACKLIST_STOP_LOSS_RATE = 0.30
"""
Stop-loss rate threshold for blacklisting pairs.
Source: Risk management practice
Rationale: If 30%+ of trades hit stop-loss, pair is problematic
          Relationship fundamentally unstable
Used in: Pair blacklist logic
"""

BLACKLIST_MIN_TRADES = 3
"""
Minimum trades before pair can be blacklisted.
Source: Statistical significance
Rationale: Need at least 3 observations to assess pattern
          1-2 bad trades could be random
Used in: Pair blacklist logic
"""

# =============================================================================
# VALIDATION PARAMETERS
# =============================================================================

CPCV_PURGE_WINDOW = 5
"""
Purge window for Combinatorial Purged Cross-Validation.
Source: López de Prado (2018) Ch.7
Rationale: Remove observations near train/test boundary
          Prevents data leakage from overlapping trades
Used in: CPCV validation, overfitting detection
"""

CPCV_EMBARGO_WINDOW = 5
"""
Embargo window after test set in CPCV.
Source: López de Prado (2018) Ch.7
Rationale: Prevent using test period information
          Gap between test and subsequent train
Used in: CPCV validation
"""

PBO_OVERFIT_THRESHOLD = 0.40
"""
PBO threshold for overfitting detection.
Source: Bailey et al. (2014) "Probability of Backtest Overfitting"
Rationale: PBO > 40% indicates strategy overfit to IS data
          Likely to fail OOS
Used in: Validation gates, overfitting detection
"""

PBO_LOW_RISK = 0.20
"""PBO < 20% = Low overfitting risk"""

PBO_MEDIUM_RISK = 0.40
"""PBO 20-40% = Medium overfitting risk"""

PBO_MODERATE_RISK = 0.60
"""PBO 40-60% = Moderate overfitting risk"""

DSR_SIGNIFICANCE_THRESHOLD = 0.0
"""
Deflated Sharpe Ratio threshold for significance.
Source: Bailey & López de Prado (2014)
Rationale: DSR < 0 means Sharpe not statistically significant
          Could be due to random luck, not skill
Used in: Validation gates
"""

RANK_CORRELATION_THRESHOLD = 0.30
"""
Minimum rank correlation (IS vs OOS) for validation.
Source: Bailey et al. (2014)
Rationale: Low correlation means top performers IS don't stay top OOS
          Indicates selection bias/overfitting
Used in: Validation gates
"""

DEGRADATION_THRESHOLD = 0.50
"""
Maximum acceptable performance degradation (IS → OOS).
Source: Practitioner knowledge
Rationale: > 50% degradation indicates strategy overfit
          Performance not robust out-of-sample
Used in: Validation warnings
"""

# =============================================================================
# COINTEGRATION DRIFT MONITORING (Session 19)
# =============================================================================

DRIFT_CHECK_FREQUENCY = 21
"""
Check cointegration drift every N days (monthly).
Source: Gregory et al. (2011), Session 19 implementation
Rationale: Monthly re-testing balances:
          - Detecting structural breaks promptly
          - Avoiding excessive testing (transaction costs)
          21 days ≈ 1 trading month
Used in: Monitor during active positions
"""

DRIFT_PVALUE_THRESHOLD = 0.15
"""
Exit if cointegration p-value exceeds this during trading.
Source: Session 19 empirical analysis
Rationale: Looser than formation (0.05) to avoid premature exits
          0.15 allows temporary degradation but catches breaks
          Empirically tested: 0.15 reduces false exits
Used in: Drift monitoring exit logic
"""

# =============================================================================
# OPTIMAL THRESHOLD CALCULATION (Vidyamurthy Ch.8)
# =============================================================================

OPTIMAL_THRESHOLD_LAMBDA = 0.2
"""
Regularization parameter for optimal threshold.
Source: Vidyamurthy (2004) Ch.8
Formula: Objective = Profit - λ × TradingCost
Rationale: λ = 0.0 ignores costs (too aggressive)
          λ = 1.0 too conservative (few trades)
          λ = 0.2 balances profit vs costs
Used in: Nonparametric optimal threshold calculation
"""

THRESHOLD_DISAGREEMENT_TOLERANCE = 0.20
"""
Maximum disagreement between white noise and nonparametric thresholds.
Source: Vidyamurthy (2004) Ch.8 implementation
Rationale: If methods differ by > 20%, spread may not be white noise
          Use nonparametric (data-driven) in this case
Used in: Optimal threshold method selection
"""

# =============================================================================
# MINIMUM DATA REQUIREMENTS
# =============================================================================

MIN_FORMATION_DATA_PCT = 0.80
"""
Minimum % of formation period data required.
Source: Statistical power requirement
Rationale: If < 80% of formation_days available, insufficient data
          Cointegration test lacks power
          Skip year rather than use bad estimates
Used in: Walk-forward validation, year skipping logic
"""

# =============================================================================
# TIME-BASED STOPS (Vidyamurthy Ch.8)
# =============================================================================

STOP_TIGHTENING_RATE = 0.15
"""
Rate at which stop-loss tightens over time.
Source: Vidyamurthy (2004) Ch.8 p.130 (concept, not exact value)
Rationale: Each half-life elapsed, stop tightens by 15%
          After 2× HL, if not converged, relationship suspect
          15% empirically chosen (NOT academically justified)
Used in: Time-based stop-loss tightening
"""

# =============================================================================
# TRANSACTION COSTS
# =============================================================================

DEFAULT_TRANSACTION_COST_BPS = 10.0
"""
Default transaction cost (basis points per trade).
Source: Market practice for retail ETF trading
Rationale: ETF bid-ask spread ~2-5 bps + slippage ~3-5 bps
          Total ~5-10 bps realistic for retail
          Institutional: 1-2 bps
Used in: PnL calculation, cost analysis
"""

# =============================================================================
# USAGE NOTES
# =============================================================================

"""
How to use these constants in your code:

# CORRECT:
from pairs_trading_etf.constants import (
    DEFAULT_MIN_CORRELATION,
    DEFAULT_MAX_CORRELATION,
    TRADING_DAYS_PER_YEAR
)

def filter_pairs(pairs, min_corr=DEFAULT_MIN_CORRELATION):
    ...

# INCORRECT (hardcoded):
def filter_pairs(pairs, min_corr=0.75):  # BAD - use constant instead
    ...

When adding new constants:
1. Add to appropriate section
2. Include docstring with:
   - Source (paper, practice, empirical)
   - Rationale (why this value?)
   - Used in (where it appears)
3. Reference in code via import
4. Update this file's "Last updated" date
"""
