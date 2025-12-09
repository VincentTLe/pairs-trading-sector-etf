# Complete Data Flow: From Raw Data to PBO Validation

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     PAIRS TRADING PIPELINE                              │
│                  (Vidyamurthy + Gatev + Bailey)                         │
└─────────────────────────────────────────────────────────────────────────┘

PHASE 1: DATA LOADING
═══════════════════════════════════════════════════════════════════════════
                          ┌─────────────────┐
                          │  Yahoo Finance  │
                          │  (2015-2024)    │
                          └────────┬────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │  Load 5 ETF prices       │
                    │  Daily close adjusted    │
                    │  2,500+ trading days     │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │  Log-transform prices    │
                    │  prices_df = ln(P_t)     │
                    │  Shape: (2,500 × 5)      │
                    └────────────┬─────────────┘
                                 │
                        ▼▼▼▼▼▼▼▼▼▼▼▼
                    PHASE 1 OUTPUT:
                    prices_df = DataFrame with log prices
                        (index: date, columns: ETF symbols)


PHASE 2: PAIR SELECTION & TRADABILITY (ONE-TIME, 2015-2016)
═══════════════════════════════════════════════════════════════════════════
 
Input window: 2015-01-01 to 2016-01-01 (252 trading days = FORMATION)
  
  Step 2.1: CORRELATION SCREENING
  ──────────────────────────────────
    prices[2015:2016] 
         │
         ├─ Calculate returns: r_t = Δln(P_t)
         │
         ├─ Compute correlation matrix (5×5)
         │
         └─ Filter: pairs where |ρ| > 0.80
            Output: 5 candidate pairs (e.g., XLY-XLV, XLY-XLI, ...)

  
  Step 2.2: DISTANCE MEASURE
  ──────────────────────────────────
    For each candidate pair:
    ┌─────────────────────────────┐
    │ Normalize: P_norm = P/P_0×100│
    │ Distance: D = Σ(P_A,n - P_B,n)²
    └────────────┬────────────────┘
                 │
                 └─→ Ranked list (top 5)

  
  Step 2.3: TRADABILITY TEST
  ──────────────────────────────────
    For each ranked pair (top 5):
    
    ┌──────────────────────────────────────┐
    │ Regression: ln(P_A) = α + γ·ln(P_B)+ε │
    │ Extract: γ, μ, σ, R²                  │
    │ Output: residuals = ε_t               │
    └───────┬────────────────────────────────┘
            │
            ├─→ Check R² > 0.70 (not spurious)
            │
            ▼
    ┌────────────────────────────────────────┐
    │ ADF Test on residuals                  │
    │ H0: Unit root (non-stationary)         │
    │ If p-value < 0.05 → STATIONARY ✓       │
    │ If p-value > 0.05 → NON-STATIONARY ✗   │
    └───────┬─────────────────────────────────┘
            │
            ├─→ Keep only stationary residuals
            │
            ▼
    ┌────────────────────────────────────────┐
    │ Half-Life Calculation                  │
    │ AR(1): ε_t = φ·ε_{t-1} + u_t           │
    │ HL = -ln(2)/ln(φ)                      │
    │ If HL < 252 days → TRADABLE ✓          │
    │ If HL > 252 days → TOO SLOW ✗          │
    └────────┬─────────────────────────────────┘
             │
             └─→ Keep pairs where HL < 6 months


  Step 2.4: BAND DESIGN (FIXED!)
  ──────────────────────────────────
    For each tradable pair:
    
    ┌────────────────────────────────────┐
    │ Calculate spread statistics        │
    │ mean: μ = E[ε_t]                   │
    │ std:  σ = SD[ε_t]                  │
    │ percentiles: 5th, 25th, 50th, ...  │
    └───────┬────────────────────────────┘
            │
            ▼
    ┌────────────────────────────────────┐
    │ Design Entry/Exit Bands            │
    │ Entry Upper = μ + 2σ               │
    │ Entry Lower = μ - 2σ               │
    │ Exit Level  = μ                    │
    │ Max Hold    = 2 × half-life        │
    └───────┬────────────────────────────┘
            │
            ▼
    ┌────────────────────────────────────┐
    │ Add Regularization (Costs)         │
    │ Widen bands by 3-4 bps             │
    │ (trading costs + slippage)         │
    └────────┬───────────────────────────┘
             │
             └─→ FINAL RULES (FROZEN!)

  
                    ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
                  PHASE 2 OUTPUT:
    tradable_pairs = [
        {
            'pair': ('XLY', 'XLV'),
            'gamma': 1.523,
            'half_life_days': 25,
            'entry_upper': 0.0342,
            'entry_lower': -0.0312,
            'exit_level': 0.0015,
            'max_hold_days': 50
        },
        ... (repeat for each tradable pair)
    ]
    
    CRITICAL: These rules are NOW FROZEN for entire backtest!


PHASE 3: WALK-FORWARD BACKTEST (2016-2024)
═══════════════════════════════════════════════════════════════════════════

Loop for each year t = 2016, 2017, ..., 2024:

  Iteration t=1 (Year 2016):
  ────────────────────────────
  
  Formation window: 2015-01-01 to 2016-01-01
  └─ Already done in Phase 2
  
  Trading window: 2016-01-01 to 2017-01-01
  
  For each day d in trading window:
  
    prices_d = [XLY_close, XLV_close, ...]  ← TODAY'S PRICES
    
    For each tradable pair:
      ┌──────────────────────────────────────────┐
      │ 1. Calculate spread: ε_d = ln(P_A) - γ·ln(P_B)
      │                                           
      │ 2. Check entry signals:                   
      │    if ε_d > entry_upper:                  
      │        BUY spread: Long A, Short B        
      │    elif ε_d < entry_lower:                
      │        SELL spread: Short A, Long B       
      │    else:                                  
      │        No signal                          
      │                                           
      │ 3. Check exit signals:                    
      │    if position_age > max_hold_days:       
      │        CLOSE (timeout)                    
      │    elif ε_d < exit_level:                 
      │        CLOSE (mean reversion caught)      
      │                                           
      │ 4. Calculate daily P&L:                   
      │    if long: PnL = d(P_A) - γ·d(P_B)       
      │    if short: PnL = -d(P_A) + γ·d(P_B)     
      │                                           
      │ 5. Track: Open positions, realized P&L    
      └──────────────────────────────────────────┘
  
  End of day d
  
  End of year t → Store daily P&L series for this year


  After all iterations t=2016...2024:
  
  ┌─────────────────────────────────────────────┐
  │ Stack all annual P&L time series            │
  │ Shape: (250 trading days/year × 9 years)    │
  │     × (N tradable pairs)                    │
  │                                             │
  │ = (2,250 days × N pairs) matrix             │
  │                                             │
  │ Cell [i,j] = daily return of pair j on day i│
  └────────┬────────────────────────────────────┘
           │
           └─→ PHASE 3 OUTPUT:
                M = matrix of walk-forward returns
                (2,250 rows × 5 columns)


PHASE 4: BAILEY CSCV VALIDATION
═══════════════════════════════════════════════════════════════════════════

Input: M from Phase 3 (2,250 trading days × 5 pairs)

  Algorithm: Combinatorial Symmetric Cross-Validation
  ──────────────────────────────────────────────────
  
  Step 1: Partition
  ┌────────────────────────────────────────┐
  │ Divide M into S=16 contiguous subsets  │
  │ Each subset ≈ 2,250/16 ≈ 140 days      │
  └─────────┬──────────────────────────────┘
            │
            └─→ Creates 16 "blocks" of consecutive trading days
  
  
  Step 2: Create All IS/OOS Combinations
  ┌────────────────────────────────────────┐
  │ Total combinations: C(16,8) = 12,780   │
  │                                        │
  │ For each combination:                  │
  │   - Choose 8 blocks → IN-SAMPLE (IS)  │
  │   - Remaining 8    → OUT-OF-SAMPLE (OOS)
  │                                        │
  │ Concatenate each set (maintain order)  │
  └─────────┬──────────────────────────────┘
            │
            └─→ 12,780 different (IS, OOS) pairs
  
  
  Step 3: For Each Combination
  ┌──────────────────────────────────────────────────┐
  │ On IS data:                                      │
  │   Rank 5 pairs by Sharpe ratio (IS performance) │
  │   Best IS pair = pair with highest IS Sharpe    │
  │                                                  │
  │ On OOS data:                                     │
  │   Calculate OOS Sharpe for each pair            │
  │   Median OOS Sharpe = middle value              │
  │   Rank 5 pairs by OOS Sharpe                    │
  │                                                  │
  │ Compare:                                        │
  │   "Is the best IS pair better than OOS median?" │
  │   if OOS(best_IS_pair) < OOS_median:            │
  │       → Underperformance detected! (count++)    │
  └──────────┬───────────────────────────────────────┘
             │
  
  Step 4: Calculate PBO
  ┌──────────────────────────────────────────┐
  │ PBO = (# underperformances) / 12,780     │
  │                                          │
  │ PBO represents:                          │
  │ Probability that overfitting occurs      │
  │                                          │
  │ Interpretation:                          │
  │ PBO < 0.05  → Low overfitting (GOOD)    │
  │ PBO > 0.20  → High overfitting (BAD)    │
  └─────────┬──────────────────────────────┘
            │
            └─→ PHASE 4 OUTPUT:
                PBO = 0.08 (example: 8% prob of overfitting)


PHASE 5: FINAL REPORTING
═══════════════════════════════════════════════════════════════════════════

Create summary statistics:

  For EACH tradable pair:
  ┌─────────────────────────────────────┐
  │ Out-of-sample metrics (from walk-forward)
  │                                       
  │ OOS Sharpe Ratio                     
  │ OOS Sortino Ratio                    
  │ OOS Max Drawdown                     
  │ OOS Total Return                     
  │ Number of round-trips                
  │ Win rate (% profitable trades)       
  │ Average profit per trade             
  │ Largest winning trade                
  │ Largest losing trade                 
  │ Holding period average               
  │ Half-life (mean reversion speed)     
  │ Gamma (hedge ratio)                  
  └──────────────────────────────────────┘
  
  For ENTIRE STRATEGY:
  ┌──────────────────────────────────┐
  │ Portfolio Metrics                 
  │                                   
  │ Cumulative OOS Return             
  │ Portfolio Sharpe Ratio            
  │ Portfolio Max Drawdown            
  │ Bailey PBO Value                  
  │ Overfitting Assessment            
  │ Recommendation                    
  └──────────────────────────────────┘
  
  
Report Conclusion:
  ┌────────────────────────────────────────┐
  │ IF PBO < 0.05:                        │
  │   "Low overfitting risk. Strategy     │
  │    appears robust based on CSCV."     │
  │                                        │
  │ IF 0.05 ≤ PBO < 0.15:                 │
  │   "Moderate overfitting risk. Cautious│
  │    interpretation recommended."        │
  │                                        │
  │ IF PBO ≥ 0.15:                        │
  │   "High overfitting risk. Parameter   │
  │    set should be reconsidered."       │
  └────────────────────────────────────────┘
```

---

## Data Structure Reference

### Phase 1 Output: `prices_df`
```python
prices_df = pd.DataFrame
├─ Index: DatetimeIndex (2015-01-01 to 2024-12-31)
├─ Columns: ['XLY', 'XLV', 'XLE', 'XLI', 'XLF']
├─ Values: log(adjusted_close)
├─ Shape: (2,500 rows × 5 columns)
└─ Example:
              XLY        XLV        XLE       XLI        XLF
   2015-01-02  4.234    4.123     3.945    4.012      4.087
   2015-01-05  4.239    4.128     3.941    4.015      4.090
   ...

```

### Phase 2 Output: `tradable_pairs`
```python
tradable_pairs = [
    {
        'pair': ('XLY', 'XLV'),
        'gamma': 1.523,                    # Hedge ratio
        'alpha': 0.002,
        'r_squared': 0.87,
        'adf_pvalue': 0.031,               # < 0.05 → stationary
        'phi': 0.935,                      # AR(1) coefficient
        'half_life_days': 25.3,
        'spread_mean': 0.00123,            # μ
        'spread_std': 0.0234,              # σ
        'entry_upper': 0.0474,             # μ + 2σ + regularization
        'entry_lower': -0.0448,            # μ - 2σ - regularization
        'exit_level': 0.0015,              # μ + slippage
        'max_hold_days': 50,               # 2 × half-life
        'residuals': np.array([...])       # For diagnostics
    },
    ...
]

# THESE VALUES ARE FROZEN! DO NOT CHANGE!
```

### Phase 3 Output: `M` (Walk-Forward Returns)
```python
M = np.array or pd.DataFrame
├─ Rows: 2,250 trading days (9 years × 250 days/year)
├─ Columns: 5 tradable pairs
├─ Values: Daily returns (e.g., -0.0023, 0.0145, ...)
├─ Shape: (2,250 × 5)
└─ Example:
             XLY-XLV   XLY-XLI   XLV-XLI   XLE-XLI   XLF-XLI
   2016-01-04  0.0013   -0.0008   0.0021   -0.0005   0.0032
   2016-01-05 -0.0042    0.0018  -0.0060    0.0123  -0.0011
   ...

```

### Phase 4 Output: `pbo_result`
```python
pbo_result = {
    'pbo': 0.0847,                    # 8.47% probability of overfitting
    'n_combinations': 12780,          # C(16,8)
    'underperformance_count': 1082,
    'interpretation': 'Moderate overfitting risk',
    'summary': 'Strategy shows some evidence of parameter fitting to data'
}
```

---

## Key Data Transformations

```
1. Raw Price → Log Price
   P_t → ln(P_t)
   Why: Makes returns additive, stabilizes variance

2. Log Prices → Residuals (Spread)
   ln(P_A) - γ·ln(P_B) = ε_t
   Why: Removes common trend, isolates mean-reverting component

3. Residuals → Trading Signals
   if ε_t > μ + 2σ: "Entry signal"
   Why: Deviation from mean suggests reversion opportunity

4. Prices + Signals → Daily P&L
   if position open: PnL_d = change in ε_t
   Why: Profit from mean reversion

5. Daily P&L → Matrix M
   Stack all 9 years of returns
   Why: Input for CSCV validation

6. Matrix M → PBO
   Run CSCV algorithm
   Why: Assess if parameters are overfitted
```

---

## Important Notes

1. **Formation ≠ Training**
   - Formation: Estimate parameters on fixed period
   - Training: In ML, optimize on data (NOT used here)

2. **Parameters are FROZEN**
   - Estimate once (Phase 2)
   - Use same values for entire backtest (Phase 3)
   - Never re-optimize during backtest

3. **Walk-Forward Provides OOS**
   - Each year's "trading window" is out-of-sample
   - Formation window ≠ trading window (different data)

4. **CSCV Validates Parameters**
   - Takes walk-forward results
   - Checks if parameters are robust
   - Not designed to optimize (just validate)

5. **Interpretation**
   - OOS Sharpe: Expected return (realistic)
   - PBO: Probability of overfitting (risk measure)
   - Report both, but emphasize PBO as primary validation
```

---

This complete data flow ensures:
- ✅ No data leakage
- ✅ Parameters frozen (no re-optimization bias)
- ✅ Walk-forward is true out-of-sample
- ✅ CSCV validates robustness
- ✅ Final metrics are honest (not inflated)
