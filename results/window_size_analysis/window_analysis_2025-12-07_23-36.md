# Window Size Empirical Analysis Report

Generated: 2025-12-07_23-36

## Objective

Empirically test different formation/trading window combinations to find optimal values for pairs trading strategy.

## Test Configurations

| Config | Formation | Trading | Hedge Update | Description |
|--------|-----------|---------|--------------|-------------|
| 252-252_baseline | 252 | 252 | 63 | Baseline: 1Y formation, 1Y trading (current default) |
| 252-126_gatev | 252 | 126 | 42 | Gatev baseline: 1Y formation, 6M trading |
| 120-60_moderate | 120 | 60 | 30 | Moderate: 6M formation, 3M trading |
| 120-30_aggressive | 120 | 30 | 15 | Aggressive: 6M formation, 1M trading |
| 180-90_balanced | 180 | 90 | 30 | Balanced: 9M formation, 4.5M trading |

## Results Summary

### Performance Metrics

