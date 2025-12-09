# Pairs Trading Backtest Pipeline Architecture

> **Last Updated:** December 8, 2025 (Session 21)
> **Status:** Production-ready with WFA + CSCV validation framework

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Data Flow](#data-flow)
4. [Core Components](#core-components)
5. [Pipeline Stages](#pipeline-stages)
6. [File Structure](#file-structure)
7. [Validation Framework](#validation-framework)
8. [Configuration System](#configuration-system)
9. [Usage Examples](#usage-examples)
10. [Redundancies Removed](#redundancies-removed)
11. [Outstanding Issues](#outstanding-issues)

---

## Overview

This pairs trading backtest system implements a **walk-forward validation framework** based on:
- **Vidyamurthy (2004)** - Pairs Trading: Quantitative Methods and Analysis (Chapters 5-8)
- **Bailey et al. (2016)** - The Probability of Backtest Overfitting
- **López de Prado (2018)** - Advances in Financial Machine Learning (Chapter 7)

### Key Features

1. **Walk-Forward Analysis (WFA)** - Rolling formation → trading periods, prevents look-ahead bias
2. **CSCV Diagnostic (Optional)** - Bailey et al. (2015) PBO calculation for overfitting detection
3. **Purged Walk-Forward** - Train/test splits with embargo/purge to prevent data leakage
4. **QMA Level 2 Compliance** - Fixed exit parameters to avoid Rolling Beta Trap
5. **Vidyamurthy Framework** - SNR, Zero-Crossing Rate, optimal thresholds per Chapter 8

### Validation Approach (Session 21 Update)

**Two-Layer Validation:**
- **WFA (Walk-Forward Analysis):** The PRIMARY validation method - train on past, test on future
- **CSCV (Combinatorial Symmetric CV):** OPTIONAL diagnostic for computing PBO (Probability of Backtest Overfitting)

**Note:** CPCV was removed in Session 21. Only WFA and CSCV are used now.

### What This System Does

```
INPUT:  Price data (CSV) + Config (YAML)
                    ↓
        [Walk-Forward Backtest]
                    ↓
        [Purged Walk-Forward Validation] ← Health check
                    ↓
        [CSCV Diagnostic] ← Overfitting detection
                    ↓
OUTPUT: Validated results OR rejection with reason
```

**Critical Design Philosophy:**
> "The pipeline will NOT return positive results for overfit strategies. If validation fails, it tells you WHY."

---

## Architecture Diagram

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PAIRS TRADING BACKTEST PIPELINE                   │
│                                                                       │
│  ┌───────────┐      ┌────────────┐      ┌──────────┐                │
│  │  CONFIG   │──┐   │   PRICES   │──┐   │  OUTPUT  │                │
│  │  (YAML)   │  │   │   (CSV)    │  │   │ (JSON/   │                │
│  └───────────┘  │   └────────────┘  │   │  CSV)    │                │
│                 │                    │   └──────────┘                │
│                 ▼                    ▼          ▲                     │
│         ┌──────────────────────────────────────┼───────┐             │
│         │      PIPELINE ORCHESTRATOR           │       │             │
│         │    (pipeline.py)                     │       │             │
│         └──────────────────────────────────────┼───────┘             │
│                         │                      │                     │
│         ┌───────────────┼──────────────────────┘                     │
│         │               │               │                            │
│         ▼               ▼               ▼                            │
│   ┌──────────┐   ┌────────────┐  ┌──────────────┐                   │
│   │  ENGINE  │   │ VALIDATION │  │     CSCV     │                   │
│   │ (engine) │   │(validation)│  │(cpcv_correct)│                   │
│   │          │   │            │  │              │                   │
│   │ • Pairs  │   │ • Purged   │  │ • PBO calc   │                   │
│   │   Select │   │   WF CV    │  │ • DSR calc   │                   │
│   │ • Trade  │   │ • Embargo  │  │ • Rank       │                   │
│   │   Sim    │   │ • IS/OOS   │  │   stability  │                   │
│   │ • Coint  │   │            │  │              │                   │
│   │   Monitor│   │            │  │              │                   │
│   └──────────┘   └────────────┘  └──────────────┘                   │
│         │               │               │                            │
│         └───────────────┼───────────────┘                            │
│                         ▼                                            │
│                  ┌─────────────┐                                     │
│                  │  METRICS    │                                     │
│                  │ (metrics.py)│                                     │
│                  │             │                                     │
│                  │ • PnL       │                                     │
│                  │ • Sharpe    │                                     │
│                  │ • Win Rate  │                                     │
│                  └─────────────┘                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow Through Pipeline

```
START
  │
  ├─► [1] Load Config (YAML) ──► BacktestConfig object
  │
  ├─► [2] Load Prices (CSV) ───► DataFrame with ETF prices
  │
  ▼
[3] Walk-Forward Backtest (engine.py)
  │
  ├─► Year 2010:
  │     ├─ Formation (2009 data): Select top 20 pairs
  │     └─ Trading (2010 data):   Execute trades, record PnL
  │
  ├─► Year 2011:
  │     ├─ Formation (2010 data): Re-select pairs
  │     └─ Trading (2011 data):   Execute trades
  │
  └─► ... continues through 2024
  │
  ▼
[4] Compute Embargo/Purge Parameters
  │   ├─ Average holding time → embargo_width
  │   └─ Max holding time → purge_width
  │
  ▼
[5] Purged Walk-Forward Validation (validation.py)
  │   ├─ Split: Train (2010-2017) / Test (2018-2024)
  │   ├─ Apply purge/embargo to prevent leakage
  │   ├─ Check: IS positive? OOS positive?
  │   └─ Decision: PASS or FAIL
  │
  ▼
[6] CSCV Diagnostic (cpcv_correct.py)
  │   ├─ Generate parameter variations
  │   │   • entry_sigma: [1.5, 2.0, 2.5]
  │   │   • exit_sigma: [0.0, 0.3, 0.5]
  │   ├─ Run backtest for each config
  │   ├─ Build returns matrix (T×N)
  │   ├─ Calculate:
  │   │   • PBO (Probability of Backtest Overfitting)
  │   │   • DSR (Deflated Sharpe Ratio)
  │   │   • Rank stability (Spearman correlation)
  │   │   • Performance degradation (IS→OOS)
  │   └─ Decision: PASS or FAIL
  │
  ▼
[7] Final Validation Gate
  │   ├─ Check PBO < 40%
  │   ├─ Check DSR > 0.0
  │   ├─ Check OOS mean > 0
  │   └─ Check Walk-Forward PASSED
  │
  ▼
[8] Output Results
  │   ├─ trades.csv
  │   ├─ summary.csv
  │   ├─ pipeline_result.json
  │   ├─ cpcv_report.txt
  │   ├─ validation_summary.txt
  │   └─ config_snapshot.yaml
  │
END
```

---

## Core Components

### 1. Configuration (`config.py`)

**Purpose:** Centralized parameter management for all backtest settings.

**Key Classes:**
- `BacktestConfig` - Main configuration dataclass with 70+ parameters

**Key Functions:**
- `load_config(path)` - Load config from YAML file
- `compute_optimal_threshold(slippage_bps)` - **Vidyamurthy Ch.8** white noise formula
- `compute_nonparametric_threshold(spread, ...)` - **Vidyamurthy Ch.8** data-driven approach
- `bootstrap_holding_period(spread_series, ...)` - Estimate holding period distribution

**Parameter Categories:**
```python
BacktestConfig:
    # Time windows
    formation_days: 252  # 1 year pair selection
    trading_days: 252    # 1 year trading

    # Pair selection (Vidyamurthy Ch.6)
    pvalue_threshold: 0.05        # Engle-Granger cointegration
    min_half_life: 2.0            # Too fast = noise
    max_half_life: 50.0           # Too slow = inefficient
    min_correlation: 0.75         # Minimum correlation
    max_correlation: 0.95         # Maximum (avoid identical)

    # Trading signals (Vidyamurthy Ch.8)
    use_optimal_entry_threshold: False  # If True, compute optimal Δ per pair
    optimal_threshold_method: 'nonparametric'  # 'white_noise' or 'nonparametric'
    optimal_threshold_lambda: 0.2  # Regularization parameter
    entry_threshold_sigma: 2.0    # Legacy fallback (if optimal=False)
    exit_threshold_sigma: 0.0     # Exit at equilibrium
    stop_loss_sigma: 4.0          # Z-score stop

    # Position management
    max_holding_days: 60          # Time-based exit
    dynamic_max_holding: True     # Scale by half-life
    max_positions: 10             # Concurrent positions

    # QMA Level 2 (CRITICAL for correctness)
    use_fixed_exit_params: True   # Prevents Rolling Beta Trap

    # Vidyamurthy tradability filters (Ch.7)
    min_snr: 0.0                  # Signal-to-Noise Ratio
    min_zero_crossing_rate: 0.0   # Zero crossings per year
    time_based_stops: True        # Tightening stops per Ch.8

    # Cointegration drift monitoring (NEW - Session 19)
    enable_cointegration_monitoring: True   # Enable drift detection
    coint_check_frequency_days: 21          # Check every ~monthly
    coint_drift_pvalue_threshold: 0.15      # Exit if p-value > 0.15
    coint_drift_lookback_days: 60           # Rolling window for re-testing
    coint_drift_min_observations: 30        # Minimum observations for valid test
```

### 2. Backtest Engine (`engine.py`)

**Purpose:** Core trading simulation with walk-forward logic.

**Key Functions:**

#### Pair Selection
```python
select_pairs(
    formation_prices: pd.DataFrame,
    cfg: BacktestConfig,
    blacklist: Optional[PairBlacklist] = None,
    formation_year: Optional[int] = None
) -> Tuple[List, Dict, Dict, Dict, Dict]:
    """
    Select cointegrated pairs using formation period data.

    Process:
    1. Test all ETF combinations for cointegration (Engle-Granger)
    2. Filter by p-value, half-life, correlation, SNR, ZCR
    3. Apply sector diversification (max_pairs_per_sector)
    4. Rank by p-value (lower = stronger cointegration)
    5. Select top N pairs
    6. [NEW] Compute optimal entry threshold per pair (if enabled)

    Returns:
    -------
    selected_pairs : List[Tuple[str, str]]
    hedge_ratios : Dict[Tuple, float]
    half_lives : Dict[Tuple, float]
    formation_stats : Dict[Tuple, Dict]
    optimal_deltas : Dict[Tuple, float]  # NEW in Session 18
    ```

#### Trading Simulation
```python
run_trading_simulation(
    trading_prices: pd.DataFrame,
    pairs: List[Tuple[str, str]],
    hedge_ratios: Dict,
    half_lives: Dict,
    cfg: BacktestConfig,
    formation_prices: pd.DataFrame,
    blacklist: Optional[PairBlacklist] = None,
    optimal_deltas: Optional[Dict] = None  # NEW in Session 18
) -> Tuple[List[Dict], float]:
    """
    Execute trading logic for selected pairs.

    Signal Generation:
    - Entry: z-score crosses ±entry_threshold (or optimal Δ)
    - Exit: Convergence (z near 0), max holding, or stop-loss

    QMA Level 2 Compliance:
    - Capture (μ_entry, σ_entry) at entry time
    - Use FIXED params for exit z-score calculation
    - Prevents "Rolling Beta Trap" where exit z uses different distribution

    Returns:
    -------
    trades : List[Dict]  # One entry per trade
    final_capital : float
    """
```

#### Walk-Forward Backtest
```python
run_walkforward_backtest(
    prices: pd.DataFrame,
    cfg: BacktestConfig,
    start_year: int = 2010,
    end_year: int = 2024,
    blacklist: Optional[PairBlacklist] = None
) -> Tuple[List[Dict], Dict[str, Any]]:
    """
    Run walk-forward backtest across multiple years.

    Structure:
    For each year Y in [start_year, end_year]:
        Formation Phase:
            - Use year Y-1 data
            - Select pairs, compute hedge ratios
            - [NEW] Compute optimal threshold per pair

        Trading Phase:
            - Use year Y data
            - Execute trades with selected pairs
            - [NEW Session 19] Monitor cointegration drift during trading
            - Record all trade details

    Returns:
    -------
    all_trades : List[Dict]
    summary : Dict  # Aggregated statistics
    """
```

#### Cointegration Drift Monitoring (NEW - Session 19)
```python
monitor_cointegration_drift(
    prices: pd.DataFrame,
    pair: Tuple[str, str],
    lookback_days: int = 60,
    pvalue_threshold: float = 0.15,
    min_observations: int = 30,
    use_log: bool = True
) -> Dict[str, Any]:
    """
    Monitor cointegration drift during trading period.

    CRITICAL FIX: Pairs were previously tested ONCE during formation,
    then traded for 252 days without re-testing. This function detects
    when cointegration relationships break down mid-trading.

    Process:
    1. Extract recent prices (lookback_days window)
    2. Re-run Engle-Granger cointegration test
    3. Compare p-value against threshold (0.15, looser than formation 0.05)
    4. Calculate current hedge ratio and half-life
    5. Return drift status and diagnostics

    Called every 21 days (monthly) during active positions.
    If p-value > 0.15, exit position immediately.

    Academic Justification:
    - Gregory et al. (2011): Cointegration monitoring essential
    - Nath (2003): Cointegration can be unstable over time
    - Vidyamurthy Ch.7: Tradability must persist

    Returns:
    -------
    {
        'drift_detected': bool,      # True if p-value > threshold
        'pvalue': float,              # Current cointegration p-value
        'hedge_ratio': float,         # Current hedge ratio
        'half_life': float,           # Current half-life (days)
        'observations': int,          # Data points in test
        'test_valid': bool,           # Sufficient observations?
        'reason': str,                # Explanation if drift detected
    }
    ```

**Vidyamurthy Framework Functions:**
```python
calculate_snr(spread, half_life) -> float
    """Signal-to-Noise Ratio (Vidyamurthy Ch.6)"""

calculate_zero_crossing_rate(spread, lookback) -> Tuple[float, float]
    """Zero-crossing rate and expected holding period (Ch.7)"""

calculate_time_based_stop(entry_time, current_time, half_life, base_stop, ...) -> float
    """Tightening stop-loss per Vidyamurthy Ch.8"""
```

### 3. Validation (`validation.py`)

**Purpose:** Purged walk-forward cross-validation to detect data leakage.

**Key Classes:**
- `PurgedWalkForwardValidator` - Implements purged CV with embargo
- `WalkForwardValidationResult` - Validation outcome with IS/OOS metrics

**How It Works:**
```python
validator = PurgedWalkForwardValidator(
    train_years=1,  # Train on 1 year
    test_years=1,   # Test on 1 year
    purge_days=21,  # Purge 21 days at boundaries
    embargo_days=5  # Embargo 5 days after test
)

result = validator.validate(prices, config)

if result.passed:
    print("Strategy is robust!")
else:
    print(f"Failed: {result.failure_reasons}")
```

**Purging Logic:**
```
Timeline: [Train Data] | Purge | [Test Data] | Embargo

Example (holding_time = 60 days):
    Jan 1 ────► Dec 31  │ XXX │ Jan 1 ──► Dec 31 │ XXX
    [Train: 2010]       │purge│ [Test: 2011]    │embargo
                        └─────┘                 └─────┘
                        21 days                 5 days
                        (remove to prevent      (prevent future
                         train/test overlap)     leakage)
```

### 4. CSCV Diagnostic (`cpcv_correct.py`)

**Purpose:** Detect overfitting using combinatorial cross-validation (Bailey et al. 2015).

**Key Classes (Session 21 Update):**
- `CSCVAnalyzer` - Combinatorial Symmetric Cross-Validation for PBO calculation
- `WalkForwardValidator` - Walk-forward analysis with purge/embargo
- `CSCVConfig` / `CSCVResult` - Configuration and result dataclasses

**Removed in Session 21:**
- `CPCVAnalyzer` - Was incorrectly named (not from Bailey paper)

**Metrics Computed:**

1. **PBO (Probability of Backtest Overfitting)**
   ```
   PBO = Prob(IS Sharpe > OOS Sharpe)

   If PBO > 40%:
       → Strategy likely overfit to in-sample data
       → Out-of-sample performance will degrade
   ```

2. **DSR (Deflated Sharpe Ratio)**
   ```
   DSR = (Sharpe - E[max_Sharpe]) / σ[Sharpe]

   E[max_Sharpe] = (1 - γ)Φ⁻¹(1 - 1/T) + γΦ⁻¹(1 - 1/T·e⁻¹)

   where:
       T = number of trials (parameter variations tested)
       γ = Euler-Mascheroni constant ≈ 0.5772

   If DSR < 0:
       → Sharpe is not statistically significant
       → Could be due to random luck
   ```

3. **Rank Stability (Spearman ρ)**
   ```
   ρ = Spearman correlation between:
       - IS rankings
       - OOS rankings

   If ρ < 0.3:
       → Top performers in-sample don't stay top out-of-sample
       → Indicates overfitting
   ```

4. **Performance Degradation**
   ```
   Degradation = (Mean_IS - Mean_OOS) / Mean_IS

   If degradation > 50%:
       → Performance drops by >50% out-of-sample
       → Strategy not robust
   ```

**Usage:**
```python
from pairs_trading_etf.backtests import CSCVAnalyzer, WalkForwardValidator

# CSCV for PBO calculation (diagnostic)
analyzer = CSCVAnalyzer(n_splits=10)
result = analyzer.analyze(returns_matrix, strategy_names)
print(f"PBO: {result.pbo:.2%}")
print(f"DSR: {result.dsr:.2f}")

# Walk-Forward Validator (primary validation)
wf = WalkForwardValidator(
    train_years=1,
    test_years=1,
    purge_days=21,
    embargo_days=10
)
wf_result = wf.analyze(returns_matrix, dates, strategy_names)
print(f"WF PBO: {wf_result.pbo:.2%}")
```

### 5. Pipeline Orchestrator (`pipeline.py`)

**Purpose:** Coordinate all components and enforce validation gates.

**Key Functions:**
```python
run_validated_backtest(
    prices: pd.DataFrame,
    config: BacktestConfig,
    pipeline_config: PipelineConfig
) -> PipelineResult:
    """
    Run complete validated backtest pipeline.

    Steps:
    1. Run walk-forward backtest
    2. Compute purge/embargo from trades
    3. Run purged walk-forward validation
    4. Generate parameter variations
    5. Run CSCV diagnostic
    6. Apply validation gates
    7. Return validated result or rejection

    Validation Gates:
    - PBO < max_pbo (default 40%)
    - DSR > min_dsr (default 0.0)
    - OOS mean > 0
    - Walk-forward PASSED

    If ANY gate fails → result.is_valid = False
    """
```

**PipelineResult Structure:**
```python
@dataclass
class PipelineResult:
    is_valid: bool                    # Overall validation status
    trades: List[Dict]                 # All trades
    summary: Dict[str, Any]           # Performance summary
    cscv_result: Optional[CPCVResult] # CSCV diagnostics
    walkforward_result: Optional[WalkForwardValidationResult]
    validation_report: str            # Human-readable report
    failure_reasons: List[str]        # Why it failed (if applicable)
    warnings: List[str]               # Non-fatal issues
```

### 6. Metrics (`metrics.py`)

**Purpose:** Calculate performance metrics and generate reports.

**Key Functions:**
```python
calculate_performance_metrics(trades: List[Dict]) -> Dict:
    """
    Calculate comprehensive performance metrics.

    Returns:
    -------
    {
        'total_pnl': float,
        'total_trades': int,
        'win_rate': float,
        'profit_factor': float,
        'avg_win': float,
        'avg_loss': float,
        'max_drawdown': float,
        'sharpe_ratio': float,
        'avg_holding_days': float,
        ...
    }
    """

pnl_by_exit_reason(trades: List[Dict]) -> pd.DataFrame:
    """Group PnL by exit reason (convergence, stop_loss, max_holding)"""

pnl_by_sector(trades: List[Dict]) -> pd.DataFrame:
    """Group PnL by sector combination"""

print_backtest_report(trades, summary, config):
    """Print formatted console report"""

save_results(trades, summary, config, output_dir):
    """Save results to CSV/JSON files"""
```

---

## Pipeline Stages

### Stage 0: Initialization

**Input:** Config file path
**Process:**
1. Load YAML config → `BacktestConfig` object
2. Load price data CSV → `pd.DataFrame`
3. Validate data integrity (no NaNs, sufficient history)

**Output:** Validated config + price data

---

### Stage 1: Walk-Forward Backtest

**Input:** Prices + Config
**Process:**

For each year Y from `start_year` to `end_year`:

**Formation Phase (Year Y-1):**
1. Filter pairs by correlation (0.75-0.95)
2. Test cointegration via Engle-Granger
3. Calculate half-life (HL) for each pair
4. Filter by HL bounds (2-50 days)
5. Calculate SNR (Signal-to-Noise Ratio)
6. Calculate ZCR (Zero-Crossing Rate)
7. Filter by SNR ≥ min_snr, ZCR ≥ min_zcr
8. Apply sector diversification limits
9. Rank by cointegration p-value (ascending)
10. Select top N pairs
11. **[NEW Session 18]** Compute optimal entry threshold per pair

**Trading Phase (Year Y):**
1. For each selected pair:
   - Calculate z-score using adaptive lookback (4× half-life)
   - Entry signals: z crosses ±entry_threshold (or optimal Δ)
   - Exit signals:
     - Convergence: |z| ≤ exit_tolerance
     - Max holding: days_held ≥ max_holding_days
     - Stop-loss: |z| ≥ stop_loss_sigma
     - **[NEW Session 19] Cointegration drift: p-value > 0.15**
   - Position sizing: capital_per_pair / max_positions
   - Record trade details

2. **[NEW Session 19] Monitor cointegration drift:**
   - Every 21 trading days (monthly)
   - Re-test cointegration on 60-day rolling window
   - If p-value > 0.15, exit immediately
   - Prevents trading pairs whose relationship has broken

3. Apply QMA Level 2 exit logic:
   - Capture (μ_entry, σ_entry) at entry
   - Calculate exit z-score using FIXED params
   - Prevents Rolling Beta Trap

**Output:**
- `all_trades`: List of trade dictionaries
- `summary`: Aggregated statistics

---

### Stage 2: Purge/Embargo Computation

**Input:** Trade list
**Process:**
1. Calculate average holding time from trades
2. Calculate max holding time from trades
3. Set embargo_width = ceil(avg_holding_days)
4. Set purge_width = ceil(max_holding_days)
5. Log values for transparency

**Output:** Purge/embargo parameters

---

### Stage 3: Purged Walk-Forward Validation

**Input:** Prices + Config + Purge params
**Process:**
1. Split data into train/test (e.g., 2010-2017 / 2018-2024)
2. Apply purge at train/test boundary
3. Apply embargo after test period
4. Run backtest on train → IS returns
5. Run backtest on test → OOS returns
6. Calculate metrics:
   - IS mean return
   - OOS mean return
   - Positive ratio: % of positive OOS periods
7. Check pass criteria:
   - OOS positive ratio ≥ 55%
   - OOS mean ≥ 0

**Output:** `WalkForwardValidationResult` with pass/fail status

---

### Stage 4: CSCV Diagnostic

**Input:** Prices + Config
**Process:**

1. **Generate parameter grid:**
   ```python
   variations = {
       'entry_threshold_sigma': [1.5, 2.0, 2.5],
       'exit_threshold_sigma': [0.0, 0.3, 0.5]
   }
   # Results in 3 × 3 = 9 configurations
   ```

2. **Run backtest for each config:**
   - Execute full walk-forward backtest
   - Extract returns time series
   - Build returns matrix (T × N)

3. **Perform CSCV:**
   - Generate all valid train/test splits
   - Ensure temporal ordering (train before test)
   - Apply purge/embargo
   - Calculate IS/OOS Sharpe for each split
   - Compute PBO, DSR, rank stability, degradation

4. **Generate report:**
   - Summary statistics
   - Visual distributions (if enabled)
   - Pass/fail determination

**Output:** `CSCVResult` with diagnostic metrics

---

### Stage 5: Validation Gates

**Input:** CSCV result + Walk-forward result
**Process:**

Check each gate sequentially:

```python
GATES = [
    ('PBO', lambda: pbo < max_pbo, 'PBO too high'),
    ('DSR', lambda: dsr > min_dsr, 'DSR too low'),
    ('OOS', lambda: oos_mean > 0, 'Negative OOS returns'),
    ('Walk-Forward', lambda: wf_result.passed, 'Walk-forward failed'),
]

failures = []
for name, check, msg in GATES:
    if not check():
        failures.append(f"{name}: {msg}")

is_valid = len(failures) == 0
```

**Output:** Validation decision + failure reasons

---

### Stage 6: Results Output

**Input:** Validated pipeline result
**Process:**

Create output directory: `results/<timestamp>_<experiment_name>/`

Save files:
1. `trades.csv` - All trades with full details
2. `summary.csv` - Aggregated performance metrics
3. `pipeline_result.json` - Complete pipeline result
4. `cpcv_report.txt` - CSCV diagnostic report
5. `validation_summary.txt` - Validation outcome
6. `config_snapshot.yaml` - Exact config used
7. `metrics.yaml` - Performance metrics

**Output:** Persistent results on disk

---

## File Structure

```
src/pairs_trading_etf/
├── backtests/
│   ├── __init__.py              # Module exports
│   ├── config.py                # BacktestConfig + optimal threshold functions
│   ├── engine.py                # Core trading simulation engine
│   ├── pipeline.py              # Pipeline orchestrator
│   ├── validation.py            # Purged walk-forward validator
│   ├── cpcv_correct.py          # CSCV/CPCV implementation (RECOMMENDED)
│   ├── cpcv.py                  # Legacy CPCV (DEPRECATED - has logic issues)
│   ├── cscv_backtest.py         # CSCV backtest wrapper (DEPRECATED)
│   └── metrics.py               # Performance metrics calculation
│
├── utils/
│   ├── __init__.py
│   ├── statistics.py            # Shared statistical functions
│   ├── sectors.py               # ETF sector mapping
│   └── validation.py            # Additional validation helpers
│
└── data/
    └── ...

scripts/
├── run_backtest.py              # ⭐ MAIN CLI - Run full validated pipeline
├── run_quick_backtest.py        # Fast testing for development
├── run_cscv_analysis.py         # ⭐ CSCV parameter sweep (renamed Session 21)
├── visualize_trade_v2.py        # Visualize individual trades
├── visualize_backtest_summary.py # Dashboard and summary plots
├── download_fresh_data.py       # Download ETF price data
├── download_global_data.py      # Download global ETF data (optional)
└── archive/                     # Archived experimental scripts

configs/
└── experiments/
    ├── default.yaml             # Base configuration
    ├── vidyamurthy_practical.yaml  # Vidyamurthy framework (empirical)
    ├── vidyamurthy_optimal.yaml    # ⭐ NEW: Per-pair optimal thresholds
    └── balanced_stop_loss.yaml     # Alternative stop-loss config

docs/
├── README.md                    # ⭐ NEW Session 19: Documentation guide
├── research_log.md              # Complete session history (UPDATED Session 19)
├── pipeline_architecture.md     # ⭐ THIS FILE (UPDATED Session 19)
├── bugs_to_fix.md               # Bug tracker
├── week2_work_summary.md        # Week 2 progress summary
├── sessions/                    # ⭐ NEW Session 19: Session summaries
│   ├── SESSION_19_EXECUTIVE_SUMMARY.md
│   ├── SESSION_18_CLEANUP_SUMMARY.md
│   └── ...
├── analysis/                    # ⭐ NEW Session 19: Technical analysis
│   ├── CRITICAL_FIXES_SESSION_19.md
│   ├── WINDOW_SIZE_ANALYSIS_PRELIMINARY.md
│   ├── OPTIMAL_THRESHOLD_IMPLEMENTATION.md
│   └── ...
└── archive/                     # ⭐ NEW Session 19: Historical/deprecated docs
    ├── debug_summary.md
    ├── v2_vs_v3_comparison.md
    └── ...
```

### File Responsibility Matrix

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| config.py | ~770 | Configuration management | `BacktestConfig`, `load_config` |
| engine.py | ~1800 | Trading simulation | `select_pairs`, `run_trading_simulation`, `run_walkforward_backtest` |
| pipeline.py | ~840 | Pipeline orchestration | `run_validated_backtest`, `quick_validate` |
| validation.py | ~730 | Walk-forward CV | `PurgedWalkForwardValidator` |
| cpcv_correct.py | ~680 | **WFA + CSCV** | `CSCVAnalyzer`, `WalkForwardValidator` |
| pair_selection.py | ~400 | Pair selection | `select_pairs`, `run_engle_granger_test` |
| signal_generation.py | ~400 | Signal logic | `generate_entry_signals`, `check_exit_conditions` |
| position_management.py | ~520 | Position tracking | `PositionManager`, `calculate_trade_pnl` |
| metrics.py | ~260 | Performance metrics | `calculate_performance_metrics` |

---

## Validation Framework

### Two-Layer Validation (Session 21 Update)

```
Layer 1: Walk-Forward Analysis (WFA) - PRIMARY
         ├─ Prevents look-ahead bias
         ├─ Mimics real trading (formation → trading)
         ├─ Purge/embargo prevents data leakage
         └─ Used for all backtests

Layer 2: CSCV Diagnostic - OPTIONAL
         ├─ Computes PBO (Probability of Backtest Overfitting)
         ├─ Tests robustness to parameter variations
         └─ Bailey et al. (2015) methodology
```

**Note:** CPCV was removed in Session 21. The pipeline now uses only WFA + CSCV.

### When Each Layer Catches Problems

| Problem | Detected By | Why |
|---------|-------------|-----|
| Look-ahead bias | Walk-Forward | Uses future data in formation |
| Data leakage | Purged WF CV | Overlapping train/test periods |
| Parameter overfitting | CSCV | Performance sensitive to small param changes |
| Selection bias | CSCV | Different params give different ranks |
| Luck vs skill | CSCV DSR | Sharpe not statistically significant |

### Validation Thresholds (Default)

```python
# CSCV thresholds
max_pbo = 0.40            # PBO < 40%
min_dsr = 0.0             # DSR > 0
require_positive_oos = True
max_degradation = 0.50     # Warning only

# Walk-forward thresholds
min_positive_ratio = 0.55  # ≥55% of periods positive
min_oos_return = 0.0       # OOS mean ≥ 0

# Purge/embargo (dynamic, based on holding time)
default_purge = 21         # Fallback if no trades
default_embargo = 5        # Fallback
```

---

## Configuration System

### Configuration Hierarchy

```
1. Default values in BacktestConfig dataclass
            ↓
2. YAML file (configs/experiments/*.yaml)
            ↓
3. Command-line overrides (--param value)
```

### Example Config: vidyamurthy_optimal.yaml

```yaml
experiment_name: vidyamurthy_optimal
description: "Vidyamurthy Ch.8 with per-pair optimal thresholds"

# ============================================================================
# CH.8: OPTIMAL THRESHOLD SELECTION ⭐ KEY DIFFERENCE
# ============================================================================
use_optimal_entry_threshold: true  # Compute optimal Δ per pair
optimal_threshold_method: 'nonparametric'  # Data-driven approach
optimal_threshold_lambda: 0.2  # Regularization parameter

# Pair selection (Vidyamurthy Ch.6)
pvalue_threshold: 0.05
min_half_life: 2.0
max_half_life: 50.0
min_correlation: 0.75
max_correlation: 0.95

# Trading signals
exit_threshold_sigma: 0.5
exit_tolerance_sigma: 0.0
stop_loss_sigma: 99.0  # Effectively disabled

# QMA Level 2 (CRITICAL)
use_fixed_exit_params: true  # Prevent Rolling Beta Trap
use_adaptive_lookback: true  # lookback = 4 × half_life

# Position management
max_holding_days: 60
dynamic_max_holding: true
max_holding_multiplier: 3.0
max_positions: 10

# Vidyamurthy tradability filters (Ch.7)
min_snr: 0.0
min_zero_crossing_rate: 0.0
time_based_stops: true
stop_tightening_rate: 0.15

# Capital
initial_capital: 50000
capital_per_pair: 10000
leverage: 1.0
compounding: false

# Costs
transaction_cost_bps: 10.0  # 10 bps per trade
```

### Loading Configuration

```python
# Method 1: Load from YAML
from pairs_trading_etf.backtests import load_config

cfg = load_config('configs/experiments/vidyamurthy_optimal.yaml')

# Method 2: Programmatic creation
from pairs_trading_etf.backtests import BacktestConfig

cfg = BacktestConfig(
    experiment_name="test",
    pvalue_threshold=0.05,
    entry_threshold_sigma=2.0,
    # ... other params ...
)

# Method 3: Merge with overrides
base_cfg = load_config('configs/experiments/default.yaml')
overrides = {'entry_threshold_sigma': 2.5, 'max_positions': 15}
cfg = merge_configs(base_cfg, overrides)
```

---

## Usage Examples

### Example 1: Basic Backtest (No Validation)

```python
from pairs_trading_etf.backtests import run_walkforward_backtest, load_config
import pandas as pd

# Load data and config
prices = pd.read_csv('data/raw/etf_prices_fresh.csv', index_col=0, parse_dates=True)
cfg = load_config('configs/experiments/default.yaml')

# Run backtest
trades, summary = run_walkforward_backtest(
    prices,
    cfg,
    start_year=2010,
    end_year=2024
)

print(f"Total PnL: ${summary['total_pnl']:.2f}")
print(f"Win Rate: {summary['win_rate']:.1%}")
```

### Example 2: Full Validated Pipeline (Recommended)

```python
from pairs_trading_etf.backtests import run_validated_backtest, load_config, PipelineConfig
import pandas as pd

# Load data and config
prices = pd.read_csv('data/raw/etf_prices_fresh.csv', index_col=0, parse_dates=True)
cfg = load_config('configs/experiments/vidyamurthy_optimal.yaml')

# Configure pipeline
pipeline_cfg = PipelineConfig(
    run_cpcv=True,
    cpcv_n_splits=10,
    max_pbo=0.40,
    min_dsr=0.0,
    run_walkforward_validator=True
)

# Run validated backtest
result = run_validated_backtest(prices, cfg, pipeline_cfg)

if result.is_valid:
    print(" Strategy PASSED validation!")
    print(result.validation_report)
    print(f"Total PnL: ${result.summary['total_pnl']:.2f}")
    print(f"PBO: {result.cscv_result.pbo:.2%}")
    print(f"DSR: {result.cscv_result.dsr:.2f}")
else:
    print("❌ Strategy FAILED validation:")
    for reason in result.failure_reasons:
        print(f"  - {reason}")
```

### Example 3: CLI Usage (scripts/run_backtest.py)

```bash
# Full validation (default)
python scripts/run_backtest.py \
    --config configs/experiments/vidyamurthy_optimal.yaml \
    --start 2010 \
    --end 2024

# Quick mode (skip CSCV for debugging)
python scripts/run_backtest.py \
    --config configs/experiments/default.yaml \
    --no-cpcv \
    --no-walkforward

# CSCV parameter sweep
python scripts/run_cpcv_analysis.py \
    --config configs/experiments/vidyamurthy_optimal.yaml \
    --sweep \
    --walk-forward \
    --entry-sigma 1.5 2.0 2.5 \
    --exit-sigma 0.0 0.3 0.5
```

### Example 4: Compute Optimal Threshold

```python
from pairs_trading_etf.backtests.config import (
    compute_optimal_threshold,
    compute_nonparametric_threshold
)
import numpy as np

# White noise optimal (formula-based)
delta_wn = compute_optimal_threshold(slippage_bps=10.0)
print(f"White noise optimal: {delta_wn:.4f}σ")
# Output: 0.7518σ (computed, not hardcoded)

# Nonparametric optimal (data-driven)
spread = np.random.randn(252)  # 1 year of daily data
delta_np = compute_nonparametric_threshold(
    spread,
    slippage_bps=10.0,
    lambda_reg=0.2
)
print(f"Nonparametric optimal: {delta_np:.4f}σ")
# Output: ~0.77σ (varies by data)
```

---

## Redundancies Removed

### Session 17 Cleanup (2025-12-05)

**Deleted Files:**
- `scripts/run_cv_backtest.py` - Broken imports (depends on removed cross_validation.py)
- `scripts/run_cscv_backtest.py` - Broken imports
- `scripts/test_qma_level2.py` - Missing config files
- `deprecated_cross_validation.py` - Moved to deprecated, not imported

**Code Deduplication:**
- Created `utils/statistics.py` with shared functions:
  - `expected_max_sharpe()` - Previously in cpcv.py and cpcv_correct.py
  - `calculate_dsr()` - Previously in cpcv.py and cpcv_correct.py

**Code Reduction:**
- Before: 13,574 lines
- After: 11,374 lines
- **Reduction: 2,200 lines (16%)**

### Session 18 Identified Redundancies

**Still Present (Needs Cleanup):**

1. **`bootstrap_holding_period` - Duplicate in 2 files:**
   - `config.py:584` - Full implementation with percentiles
   - `engine.py:127` - Simpler implementation
   - **Recommendation:** Keep config.py version, remove engine.py version

2. **`cpcv.py` - Legacy file (869 lines):**
   - Has logic issues per code comments
   - `cpcv_correct.py` is the correct implementation
   - Still imported in `__init__.py` for backward compatibility
   - **Recommendation:** Deprecate and move to archive after Session 18

3. **`cscv_backtest.py` - Already deprecated (537 lines):**
   - Depends on removed `cross_validation.py`
   - Commented out in `__init__.py`
   - **Recommendation:** Delete in next cleanup session

---

## Outstanding Issues

### Session 19 Critical Fixes (2025-12-07) ✅

**Fixed in Session 19:**

| Bug | Description | Status | Impact |
|-----|-------------|--------|--------|
| **Cointegration Drift** | Pairs tested ONCE then traded 252 days without re-testing | ✅ FIXED | Critical safety feature added |
| **select_pairs Return Values** | Inconsistent returns (4 vs 5 values) | ✅ FIXED | Was blocking all backtests |
| **calculate_performance_metrics** | Wrong function signature in test scripts | ✅ FIXED | Was preventing metric calculations |

**Implementation Details:**
- Added `monitor_cointegration_drift()` function (150 lines in engine.py)
- Monthly p-value re-testing (every 21 days) during trading
- Exits positions when p-value > 0.15 (looser than formation 0.05)
- 5 new config parameters for drift monitoring
- Successfully tested across 5 window size configurations

### Remaining Critical Bugs

| Bug # | Description | Status | Impact |
|-------|-------------|--------|--------|
| #13 | **stop_loss_sigma parameter not working** | ❌ NOT FIXED | Blocks all stop-loss optimization |

**Bug #13 Details:**
```python
# Testing different stop-loss values
config_a = load_config('vidyamurthy_practical.yaml')  # stop_loss_sigma = 99.0
config_b = load_config('balanced_stop_loss.yaml')     # stop_loss_sigma = 5.0

result_a = run_backtest(prices, config_a)  # PnL: +$1,061
result_b = run_backtest(prices, config_b)  # PnL: +$1,061 (IDENTICAL!)

# Hypothesis: config parameter not being read correctly in engine.py
# Possible location: engine.py line 1406
stop_loss = getattr(cfg, 'stop_loss_sigma', 4.0)  # May always use default
```

### Known Limitations

1. **Strategy Underperformance:**
   - Annual return: +0.14% (15-year backtest)
   - SPY benchmark: +20% annually
   - By design (market-neutral, low risk)

2. **ETF Universe Constraints:**
   - Limited to ~100 ETFs
   - Less idiosyncratic movement than stocks
   - Sector correlations high

3. **Vidyamurthy Ch.8 Implementation:**
   - ✅ FIXED (Session 18): No hardcoded 0.75σ fallbacks
   - All thresholds now computed per pair
   - See [OPTIMAL_THRESHOLD_IMPLEMENTATION.md](OPTIMAL_THRESHOLD_IMPLEMENTATION.md)

---

## Glossary

| Term | Definition |
|------|------------|
| **WFA** | Walk-Forward Analysis - PRIMARY validation method (formation → trading) |
| **CSCV** | Combinatorial Symmetric Cross-Validation (Bailey et al. 2015) - for PBO calculation |
| **PBO** | Probability of Backtest Overfitting - P(best IS strategy underperforms median OOS) |
| **DSR** | Deflated Sharpe Ratio - Sharpe adjusted for multiple testing |
| **Purging** | Removing data near train/test boundary to prevent leakage |
| **Embargo** | Gap between train end and test start |
| **QMA Level 2** | Fixed exit parameters to prevent Rolling Beta Trap |
| **Rolling Beta Trap** | Exit z-score using different (μ, σ) than entry, causing false signals |
| **SNR** | Signal-to-Noise Ratio - σ_stationary / σ_noise (Vidyamurthy Ch.6) |
| **ZCR** | Zero-Crossing Rate - How often spread crosses equilibrium (Ch.7) |
| **Optimal Δ** | Entry threshold that maximizes profit function (Ch.8) |
| **Cointegration Drift** | Loss of cointegration relationship during trading period |
| **Drift Monitoring** | Monthly re-testing of cointegration p-value on rolling window |

---

## References

1. **Vidyamurthy, G. (2004).** *Pairs Trading: Quantitative Methods and Analysis*. John Wiley & Sons.
   - Chapter 5: Data Requirements
   - Chapter 6: Pair Selection (distance, cointegration)
   - Chapter 7: Tradability (SNR, ZCR, half-life)
   - Chapter 8: Trading Design (optimal thresholds)

2. **Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2014).** *The Probability of Backtest Overfitting*. Journal of Computational Finance.

3. **López de Prado, M. (2018).** *Advances in Financial Machine Learning*. John Wiley & Sons.
   - Chapter 7: Cross-Validation in Finance (purging, embargo)

4. **Avellaneda, M., & Lee, J. H. (2010).** *Statistical Arbitrage in the U.S. Equities Market*. Quantitative Finance.

5. **Gregory, A. W., Nason, J. M., & Watt, D. G. (2011).** *Testing for Structural Breaks in Cointegrated Relationships*. Journal of Econometrics.
   - Justification for cointegration monitoring during trading (Session 19)

6. **Nath, P. (2003).** *High Frequency Pairs Trading with U.S. Treasury Securities: Risks and Rewards for Hedge Funds*. London Business School Working Paper.
   - Evidence that cointegration relationships can be unstable over time (Session 19)

---

*Last Updated: December 8, 2025 (Session 21) - Removed CPCV, kept only WFA + CSCV. Renamed classes for clarity.*
