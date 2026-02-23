# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cointegration-based pairs trading research system for U.S. sector ETFs. Implements a walk-forward backtest pipeline with mandatory validation (CSCV/CPCV) based on Vidyamurthy's "Pairs Trading" (Ch.5-8), Bailey's overfitting detection, and López de Prado's purged cross-validation.

**Critical Finding:** Original $9,608 backtest profit was overfit. Cross-validation reveals near-breakeven performance on unseen data.

## Build and Run Commands

```bash
# Environment setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt

# Run tests
pytest tests/                     # All tests
pytest tests/test_engine_bugs.py  # Single test file
pytest -k "test_half_life"        # Pattern match

# Run backtest (main entry point)
python scripts/run_backtest.py                                         # Default config
python scripts/run_backtest.py configs/experiments/vidyamurthy_optimal.yaml  # Specific config
python scripts/run_backtest.py --no-cpcv --no-walkforward              # Quick mode (skip validation)

# CSCV parameter sweep
python scripts/run_cpcv_analysis.py --config configs/experiments/vidyamurthy_optimal.yaml --sweep --walk-forward

# Download fresh price data
python scripts/download_fresh_data.py
```

## Architecture

### Pipeline Flow
```
Price Data (CSV) + Config (YAML)
           ↓
[Walk-Forward Backtest] (engine.py)
  - Formation Phase: Select cointegrated pairs using year Y-1 data
  - Trading Phase: Execute trades in year Y with fixed parameters
           ↓
[Purged Walk-Forward Validation] (validation.py)
  - IS/OOS splits with embargo/purge
           ↓
[CSCV Diagnostic] (cpcv_correct.py)
  - PBO, DSR, rank stability metrics
           ↓
Validated Results OR Rejection with Reason
```

### Key Modules in `src/pairs_trading_etf/`

| Module | Purpose |
|--------|---------|
| `backtests/engine.py` | Core trading simulation, pair selection, cointegration monitoring |
| `backtests/config.py` | `BacktestConfig` dataclass, optimal threshold computation |
| `backtests/pipeline.py` | Pipeline orchestrator, validation gates |
| `backtests/validation.py` | Purged walk-forward cross-validation |
| `backtests/cpcv_correct.py` | CSCV/CPCV implementation (use this, not `cpcv.py`) |
| `cointegration/engle_granger.py` | Cointegration testing |
| `ou_model/half_life.py` | OU process half-life estimation |
| `signals/zscore.py` | Z-score signal generation |

### Configuration System

Configs in `configs/experiments/*.yaml`. Key parameters:
- `entry_threshold_sigma`: Entry z-score (Vidyamurthy optimal: 0.75σ)
- `use_fixed_exit_params: true`: **Critical** - prevents Rolling Beta Trap (QMA Level 2)
- `use_optimal_entry_threshold: true`: Compute per-pair optimal threshold
- `enable_cointegration_monitoring: true`: Monthly p-value re-testing during trading

## Important Concepts

### QMA Level 2 Compliance
Exit z-scores must use the SAME (μ, σ) captured at entry time. Setting `use_fixed_exit_params: true` prevents the "Rolling Beta Trap" where exit signals use different distribution parameters.

### Cointegration Drift Monitoring
Pairs are monitored monthly during trading (`coint_check_frequency_days: 21`). If p-value exceeds threshold (0.15), position exits immediately.

### Validation Thresholds
- PBO (Probability of Backtest Overfitting) < 40%
- DSR (Deflated Sharpe Ratio) > 0
- Walk-forward OOS mean > 0

## Known Issues

| Bug | Description |
|-----|-------------|
| #13 | `stop_loss_sigma` parameter not working - different values produce identical results |

## Deprecated Files

- `backtests/cpcv.py` - Use `cpcv_correct.py` instead
- `backtests/cscv_backtest.py` - Broken imports, commented out
