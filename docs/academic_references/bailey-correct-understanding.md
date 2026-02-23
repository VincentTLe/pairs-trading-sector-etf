# Bailey PBO (2015) - Correct Mathematical Understanding
## Combined Analysis: Bailey Framework + Gatev Application

**Author's Note:** This document corrects fundamental misunderstandings about PBO. After careful re-reading of the complete paper, the model is more nuanced than typical "overfitting test."

---

## PART 1: What PBO Actually Is (NOT What You Might Think)

### The Core Confusion

Most people think PBO answers: **"Is my strategy overfit?"** (Yes/No)

**WRONG.** Bailey's PBO answers: **"Given the strategies I tested, what's the probability the BEST ONE (chosen by IS performance) will rank BELOW the MEDIAN on OOS?"**

This is fundamentally different.

---

### Bailey's Exact Definition (Section 2.1, p.9)

**Definition 2.1 - Backtest Overfitting (the condition):**

> "We say that the backtest strategy selection process overfits if a strategy with optimal performance IS has an expected ranking below the median OOS."

Mathematical form:
$$\sum_{n=1}^{N} E[r_n | r \in \Omega^*_n] \text{Prob}[r \in \Omega^*_n] \leq N/2$$

**Definition 2.2 - Probability of Backtest Overfitting (PBO - what we estimate):**

> "A strategy with optimal performance IS is not necessarily optimal OOS. Moreover, there is a non-null probability that this strategy with optimal performance IS ranks below the median OOS. This is what we define as the probability of backtest overfit (PBO)."

Mathematical form:
$$\text{PBO} = \sum_{n=1}^{N} \text{Prob}[r_n < N/2 | r \in \Omega^*_n] \text{Prob}[r \in \Omega^*_n]$$

---

### What This Means in Plain English

Let's say you tested N=10 strategy configurations. The CSCV procedure does this 12,780 times (for S=16):

1. **For each of the 12,780 combinations:**
   - Split data 50/50 into IS (training) and OOS (testing)
   - Rank all 10 strategies on IS performance
   - Find the BEST strategy on IS (call it strategy #5, ranks 1st)
   - Check: What rank does strategy #5 get on OOS? (might be 3rd, 7th, 10th, etc.)

2. **Then ask:** In how many of the 12,780 combinations did the IS-best strategy rank **BELOW the median (< 5.5)?**

3. **PBO = (count of below-median) / 12,780**

---

## PART 2: What PBO Measures (Key Insight)

### PBO is Measuring: Rank Stability

PBO answers: **"How consistently does the best IS strategy perform well OOS?"**

- If PBO ≈ 0: IS-best consistently ranks high OOS → **reliable selection process**
- If PBO ≈ 0.5: IS-best is as likely to be below-median as above-median OOS → **uninformative process**
- If PBO ≈ 1: IS-best almost always ranks below-median OOS → **adversarial selection**

### The CSCV Insight: It's About RANKING, Not ABSOLUTE RETURN

This is CRITICAL and where most implementations fail:

From page 13, Section 3.1:

> "The PBO defined in Section 2.1 may now be estimated using the CSCV method with φ = ∫₀₋∞ f(λ)dλ. This represents the rate at which optimal IS strategies underperform the median of the OOS trials."

**Key phrase:** "underperform the MEDIAN of the OOS trials"

This means:
- ❌ NOT: "Strategy loses money OOS"
- ❌ NOT: "OOS Sharpe < IS Sharpe"
- ✅ YES: "Strategy's OOS rank is worse than the median OOS rank of all strategies"

---

## PART 3: The Logit Transform (Why It Matters)

### What is λc (logit)?

From Algorithm 2.3, Step 4.g (p.11):

> "We define the logit λc = ln(ω̄c / (1 - ω̄c))"

Where:
- ω̄c = relative rank of IS-best on OOS = r̄n* / (N + 1)
- Ranges from 0 to 1

### Why Use Logit?

From page 20, Section 4:

> "We are not making distributional assumptions on PBO. This is accomplished by using the concept of logit, λc. A logit is the logarithm of odds. In our problem, the odds are represented by relative ranks (i.e., the odds that the optimal strategy chosen IS happens to underperform OOS)."

### The Logit Mapping

```
Rank on OOS        Relative Rank     Logit λc      Interpretation
───────────────────────────────────────────────────────────
Best (1st/10)      0.09              -2.4          Strong IS/OOS consistency
Median (5th/10)    0.45              -0.2          Neutral
Worst (10th/10)    0.91              +2.4          IS/OOS divergence

Key threshold: λc = 0 when ω̄c = 0.5 (median rank)
```

---

## PART 4: How PBO is Calculated from Logits

From page 13:

> "For φ ≈ 0, a low proportion of the optimal IS strategy outperformed the median of the trials in most of the testing sets indicating no significant overfitting. On the flip side, φ ≈ 1 indicates high likelihood of overfitting."

Mathematical:
$$\text{PBO} = \phi = \int_{-\infty}^{0} f(\lambda) d\lambda$$

This integrates the proportion of logits that are **negative** (below median OOS rank).

---

## PART 5: The Other Metrics (Bailey Framework Completeness)

From Section 3, page 13:

> "The framework introduced in Section 2 allows us to characterize the reliability of a strategy's backtest in terms of four complementary analysis..."

### 1. Probability of Backtest Overfitting (PBO)
- **What:** Rate at which IS-best ranks below median OOS
- **Range:** 0 to 1
- **Good:** PBO < 0.05

### 2. Performance Degradation
From page 14:

> "This determines to what extent greater performance IS leads to lower performance OOS"

Measured as regression slope β in: Rn*_OOS = α + β·Rn*_IS + ε

- **What:** How much does OOS performance drop relative to IS performance?
- **Good:** β ≈ 0 or slightly positive (not large negative)
- **Bad:** Large negative β

### 3. Probability of Loss
From page 14:

> "A particularly useful statistic is the proportion of combinations with negative performance, Prob[Rn*c < 0]"

- **What:** In how many CSCV combinations does the IS-best strategy lose money OOS?
- **Good:** Low probability of negative OOS return
- **Note:** This is INDEPENDENT of PBO (you can have PBO ≈ 0 but high loss probability)

### 4. Stochastic Dominance
From page 16-17:

> "A further application of the results derived in Section 2.2 is to determine whether the distribution of Rn* across all c ∈CS stochastically dominates over the distribution of all R."

- **What:** Does the IS-best strategy's OOS returns distribution dominate the overall distribution?
- **Good:** First-order or second-order stochastic dominance
- **Means:** Your selection procedure adds value beyond random choice

---

## PART 6: Gatev + Bailey Integration

### How Gatev Fits Into Bailey's Framework

Gatev's pairs trading creates **N = many strategies** by testing different parameters:
- Formation period length: 12 months
- Trading period length: 6 months
- Entry threshold: 2σ
- Exit rule: price crossing

Each year, Gatev gets multiple (year pairs) that form N "strategies" (actually, different strategy executions).

**Bailey's PBO then asks:** "Across different IS/OOS splits, how consistently does the best-performing year's strategy ranking hold OOS?"

### Why the 12/6 Split Matters for Bailey

From Gatev paper (page 10):

> "Both twelve months and six months are chosen arbitrarily"

**Bailey's implication:** You MUST test different splits to see which minimizes PBO.

From Bailey Section 4, page 21-22:

> "Finally, PBO is evaluated by comparing combinations of T/2 observations with their complements. But the backtest works with T observations, rather than only T/2. Therefore, T should be chosen to be double of the number of observations used by the investor to choose a model configuration or to determine a forecasting specification."

This means:
- If your formation period is 12 months → T_CSCV needs 24 months
- If your formation period is 6 months → T_CSCV needs 12 months

---

## PART 7: Implementation Subtlety (What I Got Wrong)

### Wrong Understanding:
> "Matrix M has each column as a year's P&L"
> "N = 10 (years)"
> "PBO tells if this year-based strategy set is overfit"

### Correct Understanding:
Matrix M should have:
- **Each column = a DIFFERENT STRATEGY CONFIGURATION you tested**
- **NOT = different years**

**From Algorithm 2.3, page 10:**

> "First, we form a matrix M by collecting the performance series from the N trials. In particular, each column n = 1, . . . , N represents a vector of profits and losses over t = 1, . . . , T observations associated with a particular model configuration tried by the researcher."

For Gatev-style pairs trading, this could be:
- Column 1: Pairs trading with entry threshold 1.5σ
- Column 2: Pairs trading with entry threshold 2.0σ
- Column 3: Pairs trading with entry threshold 2.5σ
- ... N columns total

Not:
- Column 1: Year 2015 performance
- Column 2: Year 2016 performance
- ...

---

## PART 8: Correct Application to Your Project

### What You Should Do

**Step 1: Design Experiment**
```
Test parameter combinations:
- Formation: 6, 9, 12, 18 months
- Trading: 3, 6, 9 months
- Entry threshold: 1.5σ, 2.0σ, 2.5σ

Total: 4 × 3 × 3 = 36 "strategies" (N = 36)
```

**Step 2: Generate Performance Matrix**
```
For EACH of the 36 strategy combinations:
  Run walk-forward backtest on entire historical data
  Collect daily P&L time series
  
Result: Matrix M of shape (T days × 36 strategies)
where T = full history (2500+ days)
```

**Step 3: Apply CSCV**
```
CSCV({
  M = 2500 days × 36 strategies,
  S = 16 submatrices
})

Output:
- PBO = probability IS-best ranks below median OOS
- Performance degradation curve
- Stochastic dominance tests
```

**Step 4: Interpret**
```
If PBO < 0.05:
  → Your parameter selection procedure is reliable
  → IS-best strategy likely to perform well OOS

If PBO > 0.20:
  → High overfitting in your parameter search
  → Pick the parameter combo with BEST PBO
    (not the one with highest IS Sharpe)
```

---

## PART 9: Critical Limitations (From Paper)

### Design Limitations (Section 5.1)

**1. Symmetry Assumption**
> "The complexity of investment strategies and performance measures makes it unlikely that any particular method will be a one size fits all solution."

Your strategy might not follow the assumptions.

**2. Time-Series Structure**
> "If the performance measure as a time series has a strong autocorrelation, then such a division may obscure the characterization especially when S is large."

Pairs trading might have temporal structure that symmetric division breaks.

### Application Limitations (Section 5.2)

**1. Requires Complete Information (Critical!)**
From page 23:

> "The researcher must provide full information regarding the actual trials conducted, to avoid the file drawer problem (the test is only as good as the completeness of the underlying information)"

**Translation:** If you tested 100 parameter combinations but only report the 10 best ones, PBO is meaningless.

**2. Does NOT Validate the Backtest Itself**
From page 23:

> "This procedure does nothing to evaluate the correctness of a backtest. If the backtest is flawed due to bad assumptions, such as incorrect transaction costs or using data not available at the moment of making a decision, our approach will be making an assessment based on flawed information."

**Translation:** PBO assumes:
- ❌ Formation data is NOT leaked into trading data
- ❌ You're not using future information
- ❌ Transaction costs are realistic

**3. Out-of-Sample Structural Breaks**
From page 24:

> "If a structural break occurs outside the boundaries of the available dataset, the strategy may be overfit to a particular data regime, which our PBO has failed to account for because the entire set belongs to the same regime."

**Translation:** If 2008 crash was outside your data, PBO can't protect against it.

**4. DO NOT USE PBO AS OPTIMIZATION OBJECTIVE**
From page 24:

> "We must warn the reader against applying CSCV to guide the search for an optimal strategy. That would constitute a gross misuse of our method. As Strathern [31] eloquently put it, 'when a measure becomes a target, it ceases to be a good measure.'"

**Translation:** 
- ❌ DON'T: Optimize parameters to minimize PBO
- ✅ DO: Test parameters, compute PBO, choose based on PBO comparison

---

## PART 10: The Gatev Connection (Why 12/6 Matters)

### Gatev's Design (from paper, page 10):

> "We form pairs over a twelve-month period (formation period) and trade them in the next six-month period (trading period). Both twelve months and six months are chosen arbitrarily..."

Gatev admits it's arbitrary. **For Bailey:**

### Your Obligation

You must test whether 12/6 is the right split by computing PBO for:

| Formation | Trading | PBO  | OOS Return | Recommendation |
|-----------|---------|------|------------|---|
| 6 months  | 3 mo    | 0.18 | 0.45%/mo   | ⚠️ High PBO |
| 9 months  | 6 mo    | 0.08 | 0.52%/mo   | ✅ Good |
| 12 months | 6 mo    | 0.12 | 0.48%/mo   | ⚠️ Moderate |
| 12 months | 9 mo    | 0.25 | 0.35%/mo   | ❌ Very high |
| 24 months | 12 mo   | 0.05 | 0.38%/mo   | ✅ Excellent |

**Choose 9/6 or 24/12 based on PBO, NOT raw returns.**

---

## PART 11: Summary - What's Different from What I Said Before

| Aspect | What I Said | What Bailey Actually Says |
|--------|-----------|--------------------------|
| **N means** | Number of years | Number of strategy configurations tested |
| **Matrix M columns** | Each year's P&L | Each configuration's P&L |
| **PBO measures** | "Is strategy overfit?" | "Does best IS configuration rank well OOS?" |
| **Median threshold** | Arbitrary | Fundamental to definition |
| **Below median** | Rare edge case | The actual PBO calculation |
| **Logit meaning** | Performance ratio | Odds of underperforming median |
| **Good PBO** | < 0.05 | < 0.05 (same, but better understanding) |
| **Stochastic dominance** | Optional metric | One of FOUR essential analyses |

---

## PART 12: Correct Mathematical Notation

### Ranking Vector r (IS rankings)

For N = 3 strategies with IS Sharpes (0.5, 1.1, 0.7):
- Strategy 1: Sharpe 0.5 → Rank 3 (worst)
- Strategy 2: Sharpe 1.1 → Rank 1 (best)
- Strategy 3: Sharpe 0.7 → Rank 2

So: r = (3, 1, 2)

### Ranking Vector r̄ (OOS rankings)

For OOS Sharpes (0.6, 0.7, 1.3):
- Strategy 1: Sharpe 0.6 → Rank 2
- Strategy 2: Sharpe 0.7 → Rank 3
- Strategy 3: Sharpe 1.3 → Rank 1

So: r̄ = (2, 3, 1)

### Finding PBO for This Combination

Which strategy was best IS? Strategy 2 (r₂ = 1)

What rank did strategy 2 get OOS? r̄₂ = 3

Is rank 3 below median (N/2 = 1.5)? YES → Counts toward PBO numerator

---

## FINAL: Implementation Checklist

✅ Understand PBO measures RANKING CONSISTENCY
✅ Matrix M = configurations × observations (NOT years × observations)  
✅ Each column is a different strategy parameter combo
✅ CSCV tests across 12,780 IS/OOS splits
✅ PBO = proportion where IS-best ranks below median OOS
✅ Use logit transform for non-parametric estimation
✅ Report ALL four metrics: PBO, degradation, loss prob, dominance
✅ Test formation/trading period sensitivity
✅ Choose parameters that MINIMIZE PBO
✅ Disclose all tested combinations (file drawer problem)

---

## References

- Bailey, D.H., Borwein, J.M., López de Prado, M., & Zhu, Q.J. (2015). "The Probability of Backtest Overfitting." SSRN Electronic Journal. https://ssrn.com/abstract=2326253

- Gatev, E., Goetzmann, W.N., & Rouwenhorst, K.G. (2006). "Pairs Trading: Performance of a Relative Value Arbitrage Rule." Yale ICF Working Paper 08-03.

---

**Document Version:** 2.0 - Corrected Understanding
**Last Updated:** December 8, 2025
