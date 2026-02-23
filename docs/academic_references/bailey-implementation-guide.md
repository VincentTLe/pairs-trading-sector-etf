# Bailey PBO Implementation Guide
## Exactly What to Implement in Your Backtest Pipeline

---

## 0. UNDERSTANDING: IS vs. OOS in Bailey's Framework

**CRITICAL:** Bailey uses "IS" and "OOS" differently than you might think!

From the paper (page 9):

> "Note that in this context IS corresponds to the subset of observations used to select the optimal strategy among the N alternatives. With IS we do not mean the period on which the investment model underlying the strategy was estimated (e.g., the period on which crossing moving averages are computed, or a forecasting regression model is estimated)."

**Translation:**
- **IS (In-Sample for Strategy Selection):** The data you use to choose which strategy configuration is "best" among N trials
- **OOS (Out-of-Sample):** The data you use to test that selected strategy
- **NOT the same as:** Formation period vs. Trading period (that's Gatev)

---

## 1. YOUR CURRENT BACKTEST PIPELINE

Based on your existing code (Gatev-based walk-forward):

```
Year Y-1 (Formation)
    ↓
Estimate cointegration, parameters
    ↓
Year Y (Trading)
    ↓
Execute trades with FIXED parameters
    ↓
Measure performance (Sharpe, return, etc.)
    ↓
Report results
```

**This is GOOD. But it's missing validation against overfitting.**

---

## 2. WHERE BAILEY FITS IN YOUR PIPELINE

### The Full Pipeline (With Bailey):

```
STEP 1: Gatev Formation-Trading Split (Already doing)
├─ Year Y-1: Formation Phase
├─ Year Y: Trading Phase
└─ Output: Single strategy performance (P&L time series)

STEP 2: Walk-Forward Loop (Already doing)
├─ Repeat Step 1 for multiple (Y-1, Y) pairs
├─ Year 1-2: Formation → Trading
├─ Year 2-3: Formation → Trading
├─ ...
├─ Year N-1, N: Formation → Trading
└─ Output: Multiple P&L time series (one per year)

STEP 3: ← YOU ARE HERE: Bailey PBO Validation (NOT doing yet)
├─ Input: All P&L time series from Step 2
├─ Create N different strategy configurations
├─ Apply CSCV algorithm
├─ Compute: PBO, Performance Degradation, Stochastic Dominance
└─ Output: PBO value + 4 diagnostic metrics

STEP 4: Decision Gate (Binary Pass/Fail)
├─ IF PBO < [your threshold] → Strategy may be valid
├─ IF PBO > [your threshold] → Strategy is probably overfit
└─ ALWAYS check: OOS mean return > 0 (essential!)

STEP 5: Report (Clean)
├─ Report OOS metrics (from Step 3)
├─ DO NOT report inflated IS metrics
└─ Include caveat: "Validated via CSCV with PBO = X%"
```

---

## 3. STEP-BY-STEP IMPLEMENTATION IN YOUR CODE

### STEP 1: After your current walk-forward backtest completes

**Location in code:** After `scripts/run_backtest.py` finishes

**What you have:**
```python
# From your current implementation:
results = {
    'year_2015': P&L_2015,  # numpy array of daily returns
    'year_2016': P&L_2016,
    'year_2017': P&L_2017,
    ...
    'year_2024': P&L_2024,
}
```

**Convert to Bailey's Format:**

```python
# Create performance matrix M for Bailey
# Shape: (T observations × N strategies)
# In your case: N = number of years (strategies)
# T = number of trading days

import numpy as np

# Collect all P&L time series
pnl_series = [
    results['year_2015'],
    results['year_2016'],
    results['year_2017'],
    ...  # one per year
]

# Convert to matrix M (T × N)
M = np.column_stack(pnl_series)
# Each column = one "strategy" (one year's trading performance)
# Each row = one observation (one trading day)

print(f"M shape: {M.shape}")  # Should be (approx 250 days × 10 years)
```

---

### STEP 2: Apply CSCV Algorithm (From Bailey Paper, Section 2.2)

**Algorithm 2.3 from paper (pages 10-12):**

```python
from scipy.special import comb
import numpy as np

class BaileyCSCV:
    def __init__(self, M, S=16):
        """
        M: Performance matrix (T × N)
           T = number of observations (days)
           N = number of strategies (years)
        S: Number of submatrices (should be even)
           Default S=16 based on Bailey recommendation
        """
        self.M = M
        self.T, self.N = M.shape
        self.S = S
        
        if self.T % S != 0:
            raise ValueError(f"T={self.T} must be divisible by S={S}")
    
    def step_1_partition(self):
        """
        Step 1: Partition M into S disjoint submatrices
        Each submatrix Ms has shape (T/S × N)
        """
        submatrix_size = self.T // self.S
        submatrices = []
        
        for s in range(self.S):
            start_idx = s * submatrix_size
            end_idx = (s + 1) * submatrix_size
            Ms = self.M[start_idx:end_idx, :]
            submatrices.append(Ms)
        
        return submatrices
    
    def step_2_combinations(self, submatrices):
        """
        Step 2: Form all combinations of S/2 submatrices
        Total combinations = C(S, S/2)
        """
        from itertools import combinations
        
        indices = list(range(self.S))
        combinations_list = list(combinations(indices, self.S // 2))
        
        return combinations_list
    
    def step_3_is_oos_split(self, submatrices, combo):
        """
        Step 3: For each combination, split into IS and OOS
        IS: rows from selected submatrices
        OOS: rows from remaining submatrices
        """
        # Training set (IS) = union of selected submatrices
        selected_rows = []
        for idx in combo:
            selected_rows.append(submatrices[idx])
        
        J_is = np.vstack(selected_rows)  # (T/2 × N)
        
        # Testing set (OOS) = complement
        unselected_indices = [i for i in range(self.S) if i not in combo]
        unselected_rows = []
        for idx in unselected_indices:
            unselected_rows.append(submatrices[idx])
        
        J_oos = np.vstack(unselected_rows)  # (T/2 × N)
        
        return J_is, J_oos
    
    def compute_sharpe_ratio(self, pnl_array):
        """
        Compute Sharpe ratio from daily returns
        pnl_array: (T × 1) array of daily P&L or returns
        """
        returns = np.diff(np.log(np.cumprod(1 + pnl_array) + 1))
        mean_ret = np.mean(returns) * 252
        std_ret = np.std(returns) * np.sqrt(252)
        
        if std_ret == 0:
            return 0
        return mean_ret / std_ret
    
    def step_4_rank_strategies(self, J):
        """
        For matrix J (IS or OOS), compute Sharpe ratio for each strategy
        Return ranking of strategies
        """
        N = J.shape[1]
        sharpes = []
        
        for n in range(N):
            sharpe = self.compute_sharpe_ratio(J[:, n])
            sharpes.append(sharpe)
        
        # Rank: 1 = best, N = worst
        ranking = np.argsort([-s for s in sharpes]) + 1
        
        return np.array(sharpes), ranking
    
    def step_5_logit(self, sharpe_is, rank_is, sharpe_oos, rank_oos, n_best):
        """
        Compute logit for the IS-best strategy on OOS
        
        n_best: which strategy was best IS (index, 0-based)
        """
        # Relative rank OOS: 1 to N
        oos_rank_of_best = rank_oos[n_best]
        
        # Normalized to [0,1]
        relative_rank_oos = oos_rank_of_best / (self.N + 1)
        
        # Logit (with small epsilon to avoid log(0))
        epsilon = 1e-8
        logit = np.log((relative_rank_oos + epsilon) / (1 - relative_rank_oos + epsilon))
        
        return logit
    
    def run(self):
        """
        Full CSCV procedure
        Returns: dict with PBO and diagnostics
        """
        submatrices = self.step_1_partition()
        combinations_list = self.step_2_combinations(submatrices)
        
        logits = []
        is_sharpes = []
        oos_sharpes = []
        oos_losses = []
        
        for combo in combinations_list:
            J_is, J_oos = self.step_3_is_oos_split(submatrices, combo)
            
            # Compute Sharpe ratios and rankings
            sharpe_is, rank_is = self.step_4_rank_strategies(J_is)
            sharpe_oos, rank_oos = self.step_4_rank_strategies(J_oos)
            
            # Find best IS strategy (index 0-based)
            n_best = np.argmax(sharpe_is)
            is_sharpes.append(sharpe_is[n_best])
            oos_sharpes.append(sharpe_oos[n_best])
            
            # Compute logit
            logit = self.step_5_logit(sharpe_is, rank_is, sharpe_oos, rank_oos, n_best)
            logits.append(logit)
            
            # Probability of loss OOS
            if sharpe_oos[n_best] < 0:
                oos_losses.append(1)
            else:
                oos_losses.append(0)
        
        # Compute PBO (proportion of logits < 0)
        logits = np.array(logits)
        pbo = np.mean(logits < 0)
        
        # Additional diagnostics
        performance_degradation = np.mean(oos_sharpes) - np.mean(is_sharpes)
        prob_oos_loss = np.mean(oos_losses)
        
        return {
            'pbo': pbo,
            'logits': logits,
            'is_sharpes': np.array(is_sharpes),
            'oos_sharpes': np.array(oos_sharpes),
            'performance_degradation': performance_degradation,
            'prob_oos_loss': prob_oos_loss,
            'num_combinations': len(combinations_list),
        }
```

---

### STEP 3: Call CSCV After Walk-Forward Completes

**Location:** End of `run_backtest.py`

```python
from bailey_cscv import BaileyCSCV

# After your walk-forward backtest
M = np.column_stack([results[year] for year in sorted(results.keys())])

# Run CSCV validation
cscv = BaileyCSCV(M, S=16)
bailey_results = cscv.run()

print("\n" + "="*60)
print("BAILEY PBO VALIDATION RESULTS")
print("="*60)
print(f"PBO (Probability of Overfitting): {bailey_results['pbo']:.2%}")
print(f"OOS Probability of Loss: {bailey_results['prob_oos_loss']:.2%}")
print(f"Performance Degradation (IS → OOS): {bailey_results['performance_degradation']:.4f}")
print(f"Mean IS Sharpe: {bailey_results['is_sharpes'].mean():.3f}")
print(f"Mean OOS Sharpe: {bailey_results['oos_sharpes'].mean():.3f}")
print("="*60)

# DECISION GATE (from Bailey paper page 13)
if bailey_results['pbo'] > 0.05:
    print("\n⚠️ WARNING: High PBO detected (> 5%)")
    print("This strategy may be OVERFIT to historical data")
else:
    print("\n✓ PBO < 5%: Strategy passes initial validation")

if bailey_results['oos_sharpes'].mean() < 0:
    print("⚠️ CRITICAL: Mean OOS Sharpe is negative!")
    print("Strategy has NO signal on unseen data")
else:
    print("✓ Mean OOS Sharpe is positive")
```

---

## 4. WHAT EACH METRIC MEANS (From Bailey Paper)

### PBO (Probability of Backtest Overfitting)

**Definition (Paper, page 9):**
> "The probability that the model configuration selected as optimal IS will underperform the median of the N model configurations OOS."

**In simple terms:**
- φ ≈ 0 → Low overfitting (IS-best often performs well OOS)
- φ ≈ 0.5 → Moderate overfitting (coin flip)
- φ ≈ 1 → High overfitting (IS-best almost always fails OOS)

**Threshold (Paper, page 13):**
> "In accordance with standard applications of the Neyman-Pearson framework, a customary approach would be to reject models for which PBO is estimated to be greater than 0.05."

**IMPORTANT:** This is a SUGGESTION, not a law. You can use 0.10 or 0.20 depending on your risk tolerance.

### Performance Degradation

**Definition (Paper, page 13-14):**
> "This determines to what extent greater performance IS leads to lower performance OOS."

**What it shows:**
```
Negative degradation = Bad (OOS much worse than IS)
Zero degradation = Good (IS ≈ OOS)
Positive degradation = Unrealistic (OOS better than IS - check for bugs)
```

### Probability of Loss (OOS)

**Definition (Paper, page 13):**
> "The probability that the model selected as optimal IS will deliver a loss OOS."

**What it means:**
- If this is 30%, your best IS strategy loses money 30% of the time OOS
- Even if PBO = 0, this can be high (strategy is just bad, not overfit)

---

## 5. DECISION FLOWCHART (From Bailey + Your Project)

```
START: Walk-Forward Complete
    ↓
Collect all yearly P&L time series
    ↓
Create matrix M (T × N)
    ↓
Run CSCV (S=16)
    ↓
COMPUTE: PBO, Degradation, OOS Loss
    ↓
┌─────────────────────────────────┐
│ Is PBO > 0.05?                  │
└─────────────────────────────────┘
    NO: Continue        YES: ⚠️ Flag as concerning
    ↓                   ↓
    │        Is mean OOS Sharpe > 0?
    │               ↙        ↘
    │              YES       NO: REJECT
    │               ↓         Strategy has
    │         Continue        no signal
    │               ↓
    └───────→ PASS: Valid strategy
             (subject to caveats)
```

---

## 6. CRITICAL IMPLEMENTATION NOTES

### NOTE 1: What is "N" in CSCV?

**In Bailey's paper:** N = number of strategy configurations you tested

**In your case:** You have two options:

**Option A (Recommended):** Use each year as a "strategy"
```python
# N = 10 years (2015-2024)
# Each "strategy" is trading performance in that year
# This tests: "Is the year-to-year performance consistent?"
```

**Option B (Alternative):** Use different parameter configurations
```python
# N = 5 different entry thresholds you tried (0.5σ, 0.75σ, 1σ, 1.5σ, 2σ)
# Each "strategy" is performance with that parameter
# This tests: "Did you overfit parameters to the data?"
```

**Recommendation:** Start with Option A (simpler, more honest).

---

### NOTE 2: What is S?

**From Bailey (page 21):**
> "For S = 16 we will obtain 12,780 logits..., and σ[f(λ)] < 0.0045, with less than a 0.01 estimation error at 95% confidence level. Also, if M contains 4 years of daily data, S = 16 would equate to quarterly partitions, and the serial correlation structure would be preserved. For these two reasons, we believe that S = 16 is a reasonable value to use in most cases."

**In your case:**
- 10 years × 250 trading days/year = 2,500 observations
- S = 16 → each submatrix = 2,500/16 ≈ 156 days (roughly 6 months)
- This is reasonable

**Use S=16 unless you have <1,000 observations, then use S=8**

---

### NOTE 3: Performance Metric

Bailey uses Sharpe ratio in examples, but paper says (page 5):

> "Although in our examples we measure performance using the Sharpe ratio, our methodology does not rely on this particular performance statistic, and it can be applied to any alternative preferred by the reader."

**In your code, I used Sharpe. You could also use:**
- Total return
- Sortino ratio  
- Calmar ratio
- Information ratio

**Just be consistent.**

---

## 7. INTEGRATION WITH YOUR EXISTING CODE

### File: `scripts/run_backtest.py`

**Current structure:**
```python
def main():
    config = load_config()
    data = load_data()
    results = run_walk_forward_backtest(config, data)
    report_results(results)  # ← Reporting inflated IS metrics

if __name__ == "__main__":
    main()
```

**NEW structure:**
```python
def main():
    config = load_config()
    data = load_data()
    
    # Step 1: Walk-forward (unchanged)
    results = run_walk_forward_backtest(config, data)
    
    # Step 2: ← NEW: Bailey validation
    bailey_results = validate_with_bailey_cscv(results)
    
    # Step 3: Report clean results
    report_validated_results(results, bailey_results)

if __name__ == "__main__":
    main()
```

### New function to add:

```python
def validate_with_bailey_cscv(results):
    """
    Apply Bailey CSCV validation to walk-forward results
    
    Input: results dict from run_walk_forward_backtest()
    Output: bailey_results dict with PBO and diagnostics
    """
    import numpy as np
    from src.validation.bailey_cscv import BaileyCSCV
    
    # Convert results to matrix format
    pnl_series = [results[year] for year in sorted(results.keys())]
    M = np.column_stack(pnl_series)
    
    # Run CSCV
    cscv = BaileyCSCV(M, S=16)
    bailey_results = cscv.run()
    
    return bailey_results
```

---

## 8. WHAT NOT TO DO (From Bailey Paper, page 26)

**DO NOT:**

> "Fifth, we must warn the reader against applying CSCV to guide the search for an optimal strategy. That would constitute a gross misuse of our method."

**This means:**

```python
# ❌ WRONG: Using PBO as optimization objective
best_params = min(params, key=lambda p: compute_pbo(p))

# ✓ CORRECT: Use PBO to EVALUATE a completed strategy
strategy_pbo = compute_pbo(params)
if strategy_pbo > 0.05:
    reject_strategy()
else:
    possibly_accept_strategy()
```

---

## 9. PUTTING IT TOGETHER: Checklist

### Before implementing Bailey PBO validation:

- [ ] Walk-forward backtest working (Gatev pipeline)
- [ ] Collecting yearly P&L time series
- [ ] Have at least 5 years of data (preferably 10+)
- [ ] Formation and trading phases properly separated

### Implementing Bailey PBO:

- [ ] Create `src/validation/bailey_cscv.py` with CSCV algorithm
- [ ] Add `validate_with_bailey_cscv()` function to `run_backtest.py`
- [ ] Set S=16 (or S=8 if <1000 observations)
- [ ] Decide N: years as strategies OR parameters as strategies
- [ ] Choose performance metric (Sharpe ratio recommended)

### After computing PBO:

- [ ] Check PBO < 0.05 (or your threshold)
- [ ] Check mean OOS Sharpe > 0 (CRITICAL)
- [ ] Check OOS probability of loss < 0.50 (reasonable)
- [ ] Check performance degradation < 0.5 (reasonable)
- [ ] Report PBO in your final summary

### Final reporting:

- [ ] Report OOS metrics, NOT inflated IS metrics
- [ ] Include caveat: "Validated via CSCV with PBO = X%"
- [ ] Mention: "PBO < 0.05 suggests low overfitting risk"
- [ ] Do NOT claim: "This strategy is profitable" - say "no statistical evidence of overfitting"

---

## 10. EXAMPLE OUTPUT

When you run the pipeline, you should see:

```
============================================================
WALK-FORWARD BACKTEST RESULTS
============================================================
In-Sample Sharpe Ratio: 1.87
(Note: This is INFLATED - for diagnostics only)

============================================================
BAILEY PBO VALIDATION RESULTS
============================================================
PBO (Probability of Overfitting): 0.08 (8%)
OOS Probability of Loss: 0.22 (22%)
Performance Degradation (IS → OOS): -0.34
Mean IS Sharpe: 1.87
Mean OOS Sharpe: 1.53

============================================================
DECISION
============================================================
✓ PBO < 5%: Strategy passes initial validation
✓ Mean OOS Sharpe is positive (1.53)
⚠ OOS Probability of Loss is 22% (acceptable)

INTERPRETATION:
The strategy shows low overfitting risk. However, mean OOS 
Sharpe of 1.53 should be considered realistic expectation, 
not the inflated IS Sharpe of 1.87.
```

---

## SUMMARY

**You need to implement Bailey at STEP 3 of your pipeline:**

1. ✅ (Already done) Gatev walk-forward
2. ✅ (Already done) Collect yearly results
3. ← **NEW:** Bailey CSCV validation (this is what you asked)
4. ← **NEW:** Report clean OOS metrics
5. ← **NEW:** Decision gate based on PBO

**Key metrics to compute:**
- PBO (main metric)
- Performance degradation
- OOS probability of loss
- Stochastic dominance (optional, advanced)

**Key decision rule:**
- IF PBO > 0.05 AND OOS Sharpe > 0 → Possibly valid
- IF PBO > 0.05 OR OOS Sharpe < 0 → Reject

**Files to create:**
1. `src/validation/bailey_cscv.py` (main algorithm)
2. Update `scripts/run_backtest.py` to call it
3. Update reporting to show OOS metrics

---

**Ready to code?** Start with the `BaileyCSCV` class implementation above.
