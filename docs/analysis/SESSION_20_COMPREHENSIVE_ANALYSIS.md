# Session 20: Comprehensive Analysis Report
**Date:** 2025-12-08
**Configuration:** Optimal 180-90 Windows
**Comparison:** Monitoring ON vs OFF
**Analysis:** Sharpe Ratio + Transaction Cost Impact

---

## Executive Summary

This session completed a comprehensive analysis of the optimal 180-90 window configuration, comparing cointegration monitoring ON vs OFF, calculating Sharpe ratios, and analyzing transaction cost impact.

### Key Findings

1. **Window Configuration:** 180-90 successfully implemented and tested
2. **Monitoring Impact:** Monitoring OFF performs BETTER (+45% higher PnL)
3. **Transaction Costs:** Strategy is HIGHLY sensitive to costs (turns negative at 5 bps)
4. **Sharpe Ratio:** 0.451 (monitoring ON) - moderate risk-adjusted returns
5. **Critical Issue:** Current transaction cost assumption (10 bps) makes strategy unprofitable

---

## 1. Configuration Implementation

### A. Optimal 180-90 Configuration

Created two configs for A/B testing:

1. **`optimal_180_90.yaml`**
   - Formation: 180 days (~9 months)
   - Trading: 90 days (~3 months)
   - Cointegration monitoring: **ON**
   - All other parameters: standard

2. **`optimal_180_90_no_monitoring.yaml`**
   - Same parameters as above
   - Cointegration monitoring: **OFF**
   - Purpose: Measure monitoring impact

### B. Rationale

- Based on Session 19 empirical findings (167% more trades vs 252-252)
- 180 days sufficient for robust cointegration testing
- 90 days matches typical half-life ranges (5-50 days)
- Shorter windows = more frequent pair re-selection = adapt to market changes

---

## 2. Backtest Results (2010-2024)

### A. Monitoring ON

```
Configuration: optimal_180_90
Monitoring: ENABLED
Period: 2010-2024

Trades:        108
Total PnL:     $411.58
Win Rate:      50.0%
Sharpe Ratio:  0.451
Max Drawdown:  -3.2%
Avg Holding:   10.9 days
```

### B. Monitoring OFF

```
Configuration: optimal_180_90_no_monitoring
Monitoring: DISABLED
Period: 2010-2024

Trades:        108
Total PnL:     $598.35
Win Rate:      50.0%
Avg Holding:   N/A (not calculated)
```

### C. Direct Comparison

| Metric              | Monitoring ON  | Monitoring OFF | Difference      |
|---------------------|----------------|----------------|-----------------|
| **Total Trades**    | 108            | 108            | 0               |
| **Total PnL**       | $+411.58       | $+598.35       | **+$186.77 (+45.4%)** |
| **Win Rate**        | 50.0%          | 50.0%          | 0%              |
| **Sharpe Ratio**    | 0.451          | N/A            | N/A             |
| **Max Drawdown**    | -3.2%          | N/A            | N/A             |
| **Avg Holding**     | 10.9 days      | N/A            | N/A             |

---

## 3. Monitoring Impact Analysis

### A. Key Finding: Monitoring OFF Outperforms

**Monitoring ON** generated **$186.77 LESS profit** (45.4% lower) than monitoring OFF.

**Why does monitoring hurt performance?**

### B. Exit Reason Breakdown

#### Monitoring ON

| Exit Reason          | Trades | Total PnL   | Avg PnL  |
|----------------------|--------|-------------|----------|
| Convergence          | 51     | $+4,590.07  | $+90.00  |
| **Coint. Drift**     | **9**  | **-$189.09** | **-$21.01** |
| Stop Loss (Time)     | 37     | $-4,379.63  | $-118.37 |
| Period End           | 3      | $-157.82    | $-52.61  |
| Max Holding          | 8      | $+548.04    | $+68.51  |

#### Monitoring OFF

| Exit Reason          | Trades | Total PnL   | Avg PnL  |
|----------------------|--------|-------------|----------|
| Convergence          | 52     | $+4,669.80  | $+89.80  |
| Stop Loss (Time)     | 40     | $-4,727.99  | $-118.20 |
| Max Holding          | 13     | $+814.36    | $+62.64  |
| Period End           | 3      | $-157.82    | $-52.61  |

### C. Drift Monitoring Issues

**Drift monitoring caused 9 exits with -$189 PnL.**

**Hypothesis:** Monitoring is too aggressive - exits positions during temporary cointegration degradation that would have recovered.

**Evidence:**
- Monitoring OFF: 13 max_holding exits (vs 8 with monitoring ON)
- These 5 additional max_holding trades: +$266 PnL
- Suggests drift exits happened prematurely

**Recommendation:** Consider relaxing drift threshold (0.15 → 0.20?) or increasing check frequency (21d → 30d?)

---

## 4. Transaction Cost Impact Analysis

### A. Cost Scenarios

Tested 4 cost assumptions on **Monitoring ON** results:

| Cost (bps) | Gross PnL | Total Costs | Net PnL    | Cost Impact | Viable? |
|------------|-----------|-------------|------------|-------------|---------|
| **0**      | $411.58   | $0.00       | $+411.58   | 0%          | ✅ Yes   |
| **5**      | $411.58   | $1,080.00   | **-$668.42** | **262%**  | ❌ No    |
| **10**     | $411.58   | $2,160.00   | **-$1,748.42** | **525%** | ❌ No   |
| **20**     | $411.58   | $4,320.00   | **-$3,908.42** | **1050%** | ❌ No  |

### B. Critical Finding: Strategy Unprofitable with Realistic Costs

**ETF trading costs:** ~5-10 bps per leg (including spread + slippage)

**With 10 bps costs:**
- Gross PnL: $+411
- Costs: $2,160 (525% of gross!)
- **Net PnL: -$1,748 (NEGATIVE)**

**Current config assumes 10 bps**, making the strategy **unprofitable in practice**.

### C. Cost Calculation Method

Each trade has **4 transactions:**
1. Buy ETF X (entry)
2. Sell ETF Y (entry)
3. Sell ETF X (exit)
4. Buy ETF Y (exit)

**Total cost per trade** = notional × 4 × cost_rate

With 108 trades averaging $10,000 notional:
- Cost per trade @ 10 bps: $10,000 × 4 × 0.001 = $40
- Total costs: 108 × $20 = $2,160

### D. Implications

1. **Strategy requires VERY low costs** (< 2 bps) to be profitable
2. **Current 10 bps assumption is realistic for retail ETF trading**
3. **Institutional costs (1-2 bps) might make strategy viable**
4. **Alternative:** Trade less frequently (longer windows?) to reduce cost drag

---

## 5. Sharpe Ratio Analysis

### A. Sharpe Ratio: 0.451

**Formula:**
```
Sharpe = (Mean Daily Return - Risk Free Rate) / Std(Daily Returns) × √252
```

**Result:** 0.451

**Interpretation:**
- **Positive:** Strategy has positive risk-adjusted returns (without costs)
- **Moderate:** 0.45 is decent but not exceptional
  - 0-1: Poor to acceptable
  - 1-2: Good
  - 2+: Excellent
- **Comparison:** SPY typically has Sharpe ~0.7-1.0

### B. Risk Metrics

```
Maximum Drawdown: -3.2%
Average Holding:  10.9 days
```

**Positive:** Low max drawdown shows controlled risk
**Concern:** Short holding period (10.9 days) → many trades → high transaction costs

---

## 6. Visualization Summary

### A. Dashboard Created

**File:** `results/figures/dashboard_quick_demo.png`

Shows:
- Cumulative PnL over time
- PnL distribution histogram
- Trades by exit reason
- Holding period distribution
- PnL by year
- Trades per year

### B. Individual Trade Visualizations

Created 6 detailed trade visualizations:
- Top 3 wins (best: EWP/EWN +$726)
- Top 3 losses (worst: EWP/EWN -$463)

Each visualization shows:
- ETF prices with LONG/SHORT labels
- % change comparison
- Z-score with entry/exit thresholds
- PnL evolution for each leg

---

## 7. Key Recommendations

### A. Transaction Costs (CRITICAL)

1. **Reduce trading frequency**
   - Longer trading windows (90 → 120 days?)
   - Higher entry threshold (2.0σ → 2.5σ?)
   - Stricter pair selection (lower p-value?)

2. **Use lower-cost execution**
   - Limit orders (not market orders)
   - Trade during high liquidity periods
   - Consider institutional broker (if accessible)

3. **Realistic cost assumptions**
   - Test with 5-10 bps (not 0)
   - Include slippage + spread
   - Factor in market impact

### B. Cointegration Monitoring

1. **Disable or relax monitoring**
   - Current version reduces PnL by 45%
   - Consider increasing p-value threshold (0.15 → 0.20)
   - Or decrease check frequency (21d → 30d)

2. **Alternative approaches**
   - Use half-life degradation instead of p-value
   - Monitor spread variance instead of cointegration
   - Apply monitoring only to losing trades

### C. Window Optimization

1. **Current 180-90 is good baseline**
   - Shows 167% more trades vs 252-252
   - But need to balance trades vs costs

2. **Consider longer trading windows**
   - 180-120 or 180-150
   - Fewer trades = lower cost impact
   - May improve Sharpe if holding period matches half-life better

---

## 8. Files Created

### Configurations
- `configs/experiments/optimal_180_90.yaml`
- `configs/experiments/optimal_180_90_no_monitoring.yaml`

### Scripts
- `scripts/run_quick_backtest.py` - Quick demo backtest
- `scripts/comprehensive_analysis.py` - Full analysis suite
- `scripts/run_monitoring_off.py` - Monitoring OFF backtest
- `scripts/create_dashboard.py` - Dashboard generation

### Results
- `results/quick_viz_trades.csv` (46 trades, 2010-2015)
- `results/optimal_180_90_monitoring_ON.csv` (108 trades, 2010-2024)
- `results/optimal_180_90_monitoring_OFF.csv` (108 trades, 2010-2024)

### Visualizations
- `results/figures/dashboard_quick_demo.png`
- `results/figures/trade_WIN_*.png` (3 files)
- `results/figures/trade_LOSS_*.png` (3 files)

---

## 9. Next Steps

### Immediate
1. **Test with realistic costs** (5-10 bps)
2. **Run sensitivity analysis** on monitoring parameters
3. **Optimize for cost efficiency** (fewer trades, higher Sharpe)

### Research Questions
1. Why does monitoring hurt performance? Is it too aggressive?
2. Can we reduce transaction costs through better execution?
3. What window size balances trades vs costs optimally?
4. Should we abandon 10 bps cost assumption?

### Technical Improvements
1. **Calculate Sharpe for monitoring OFF**
2. **Add max drawdown calculation to all backtests**
3. **Create automated comparison reports**
4. **Fix unicode encoding issues in scripts**

---

## Conclusion

This comprehensive analysis reveals **critical issues with transaction costs** that make the strategy unprofitable under realistic assumptions (10 bps). While the strategy shows positive Sharpe ratio (0.451) and controlled risk (max DD -3.2%), the **high trade frequency** combined with **short holding periods** (10.9 days) creates excessive cost drag.

**Surprisingly, cointegration drift monitoring REDUCES performance by 45%**, suggesting the monitoring is too aggressive and exits positions prematurely.

**Recommendation:** Focus on reducing trading frequency through longer windows and stricter entry criteria to make strategy viable with realistic transaction costs.

---

*Generated: 2025-12-08*
*Period: 2010-2024*
*Trades: 108 (monitoring ON) / 108 (monitoring OFF)*
*Net Result: Strategy currently unprofitable with realistic costs*
