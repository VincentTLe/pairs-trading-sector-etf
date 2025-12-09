# Pairs Trading Backtest Pipeline Architecture 2.0

> **Last Updated:** December 9, 2025
> **Status:** Running (Bug Fixed: Formation Period Mismatch)
> **Author:** Antigravity

---

## Table of Contents

1. [Overview](#overview)
2. [Current Architecture](#current-architecture)
3. [Bug Detection & Resolution](#bug-detection--resolution)
4. [Component Analysis](#component-analysis)
5. [Refactoring Recommendations](#refactoring-recommendations)

---

## Overview

This updated architecture document reflects the state of the project after debugging a critical issue where no trades were generated. The system implements a sophisticated pairs trading backtester based on Vidyamurthy (2004) and Bailey et al. (2016), featuring:

- **Walk-Forward Analysis (WFA)**: 1-year formation / 1-year trading sliding window.
- **Vidyamurthy Framework**: Cointegration testing, SNR, zero-crossing rates, and time-based stops.
- **Advanced Validation**: Purged walk-forward validation and optional CSCV (Combinatorial Symmetric Cross-Validation).
- **Consolidated Configuration**: Single YAML config driving the entire pipeline.

---

## Current Architecture

### 1. Data Flow

```mermaid
graph TD
    A[Config (YAML)] --> B[Pipeline Orchestrator]
    C[Price Data (CSV)] --> B
    B --> D[Backtest Engine]
    D --> E{Walk-Forward Loop}
    E -->|Formation Year (Y-1)| F[Pair Selection]
    F -->|Select Pairs| G[Trading Year (Y)]
    G -->|Execute Trades| H[Results]
    H --> I[Validation/Metrics]
```

### 2. Core Modules (src/pairs_trading_etf)

- **`backtests/engine.py`**: The heart of the system. Handles the walk-forward loop, calls pair selection, and executes the trading simulation.
- **`backtests/pair_selection.py`**: Implements the "Gatev/Vidyamurthy" selection logic:
  - Correlation filter (0.75 - 0.95)
  - Engle-Granger Cointegration Test (p < 0.05)
  - Half-life bounds (2 - 50 days)
  - Sector diversification limits
  - **New**: Optimal threshold calculation (White Noise / Nonparametric).
- **`backtests/signal_generation.py`**: Calculates Z-scores and checks entry/exit conditions, including the time-based stop loss logic.
- **`backtests/config.py`**: Comprehensive configuration class handling YAML loading and parameter validation.
- **`backtests/validation.py`**: Purged Walk-Forward Validator to detect overfitting.

---

## Bug Detection & Resolution

### Critical Bug: No Trades Generated

**Symptom**: The backtest ran but produced "No trades generated for the requested period" and "Insufficient formation data" warnings.
**Cause**:

- Configuration `default.yaml` specified `formation_days: 512` (approx 2 years).
- Code in `engine.py` assumes a 1-year formation window (calendar year `trading_year - 1`) which contains ~252 trading days.
- Stability check `len(data) < formation_days * 0.8` (252 < 410) failed consistently for every year.
  **Fix**: Updated `default.yaml` to `formation_days: 252`, matching the code's logic and the comment `# ~1 trading year`.

### Minor Issues Detected

- **Pandas Slicing**: The debug script initially failed because it tried to slice a DataFrame with string dates on an integer index, but the main engine correctly parses dates.
- **Time-Based Stop Performance**: The `stop_loss_time` exit reason is currently responsible for the largest losses (Avg PnL -45.0 vs Avg Win +35.0). While implemented correctly per theory, it requires parameter tuning (currently tightens 15% per half-life).

---

## Component Analysis

### Consistencies

- **Configuration**: The project successfully uses a unified `BacktestConfig` object. Parameters are consistent between `constants.py` and `default.yaml`.
- **References**: Implementation faithfully follows Vidyamurthy (Chapters 5-8), including SNR, ZCR, and optimal thresholds.

### Complexity & Clarity

- **`engine.py`**: Moderately complex (750 lines). Could be split further (e.g., extracting `run_trading_simulation` into a separate class).
- **`pair_selection.py`**: Clear and modular. Returns rich statistics.
- **`position_management.py`**: Minimal logic, mostly handling blacklist.
- **`cpcv_correct.py`**: Highly complex validation logic. Necessary for the advanced features but harder to debug.

---

## Refactoring Recommendations

1.  **Simplify `engine.py`**:

    - Extract the `run_trading_simulation` loop into a `TradingSimulator` class.
    - Move Kalman filter logic entirely to `features/kalman.py` (currently wrapped in engine).

2.  **Harmonize Formation Period**:

    - The engine hardcodes `trading_year - 1` (Calendar Year). This is rigid.
    - **Refactor**: Use `formation_days` to calculate the start date relative to `trading_year` start, allowing arbitrary formation window lengths (e.g., 2 years) as originally intended in the config.

3.  **Clean Up Legacy Files**:

    - Remove `cpcv.py` (legacy) and `cscv_backtest.py` (deprecated wrapper).
    - Remove unused scripts in `scripts/archive`.

4.  **Tune Stop-Loss**:
    - The strict time-based stop is hurting performance. Consider relaxing `stop_tightening_rate` or `MIN_STOP_LOSS_FLOOR`.

---

**Next Steps**:

- The project is now functional (trades are generated).
- Proceed with `visualize_trade_v2.py` to inspect specific losing trades.
- Consider refactoring `engine.py` to allow flexible formation windows (not just calendar years).
