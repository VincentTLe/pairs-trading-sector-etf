# Backtest Configuration Files

This directory contains YAML configuration files for running pairs trading backtests.

## Main Configurations

| Config File | Description | Use Case |
|-------------|-------------|----------|
| `default.yaml` | Full Vidyamurthy Ch.5-8 implementation with academic citations | Research, academic comparison |
| `optimal_180_90.yaml` | Empirically-tested optimal window sizes (180/90 days) | **Recommended for production** |
| `quick_backtest.yaml` | Fast testing with shorter windows | Development, debugging |
| `vidyamurthy_practical.yaml` | Vidyamurthy theory with practical thresholds | Alternative to default |

## How to Use

```bash
# Run with default config
python scripts/run_backtest.py

# Run with specific config
python scripts/run_backtest.py --config configs/experiments/optimal_180_90.yaml

# Quick test without validation
python scripts/run_backtest.py --config configs/experiments/quick_backtest.yaml --no-cpcv
```

## Key Parameters

### Formation & Trading Windows
- `formation_days`: Historical data for pair selection (typically 180-252 days)
- `trading_days`: Out-of-sample trading period (typically 90-252 days)

### Pair Selection
- `pvalue_threshold`: ADF test significance level (0.01 = strict, 0.05 = standard)
- `min_half_life` / `max_half_life`: Half-life bounds for mean reversion
- `top_pairs`: Maximum pairs to select per period

### Trading Signals
- `entry_threshold_sigma`: Z-score threshold for entry (2.0 = standard)
- `exit_threshold_sigma`: Z-score threshold for exit (0.0-0.5)
- `stop_loss_sigma`: Stop-loss threshold (3.0-4.0)

### Position Management
- `max_positions`: Maximum concurrent positions
- `max_holding_days`: Maximum days to hold a position

## Archived Configs

Experimental and legacy configs are in `archive/` directory.
