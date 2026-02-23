# Gatev (2006) - Formation & Trading Period Analysis
## Complete Extraction: NO Assumptions, Only Facts from Paper

---

## CRITICAL QUOTE ON PARAMETER CHOICE

**From Methodology Section (page 10, Section 2):**

> "Our implementation of pairs trading has two stages. We form pairs over a twelve-month period (formation period) and trade them in the next six-month period (trading period). **Both twelve months and six months are chosen arbitrarily and have remained our horizons since the beginning of the study.**"

---

## WHAT THE PAPER EXPLICITLY SAYS ABOUT THIS CHOICE

### 1. It is ARBITRARY

The paper uses the word "**arbitrarily**" - meaning:
- NOT based on theory
- NOT based on prior optimization
- NOT justified by economic argument
- NOT the result of hypothesis testing

This appears **exactly once** in the paper, on page 10.

---

### 2. What the Paper Does NOT Say

❌ **"12-month formation is optimal"** - NOT in paper
❌ **"6-month trading maximizes Sharpe ratio"** - NOT in paper
❌ **"This duration is theoretically motivated"** - NOT in paper
❌ **"We tested alternatives and chose 12/6"** - NOT in paper

The paper does NOT claim these periods are optimal or justified beyond the arbitrary choice.

---

### 3. Why They Chose This Timeframe

The paper does NOT explicitly justify the 12-month and 6-month split. However:

**What they DO say about the time dimension (page 16, Section 3.2):**

> "This indicates that pairs trading – implemented according to the particular rules we chose – is a medium-term investment strategy."

And from Table 2:

> "The average duration of an open position is 3.75 months."

This suggests the 6-month trading period was chosen because:
1. Pairs take ~3.75 months to converge on average
2. The 6-month window accommodates multiple round-trips (~2 trades per pair)
3. Allows for "medium-term" strategy implementation

**But this is INFERENCE - the paper does not state this reasoning.**

---

## DETAILED FACTS ABOUT IMPLEMENTATION

### Formation Period: 12 Months

**From page 10-11 (Section 2.1: Pairs Formation):**

> "In each pairs-formation period, we screen out all stocks from the CRSP daily files that have one or more days with no trade. This serves to identify relatively liquid stocks as well as to facilitate pairs formation. Next, we construct a cumulative total return index for each stock over the formation period."

**What happens during formation:**
1. Identify liquid stocks (traded every day for 12 months)
2. Compute cumulative total return indices
3. Find pairs using minimum distance criterion
4. Match all liquid stocks into pairs

**No optimization occurs during formation** - it's purely mechanical matching.

---

### Trading Period: 6 Months

**From page 11-12 (Section 2.2: Trading Period):**

> "Once we have paired up all liquid stocks in the formation period, we study the top 5 and 20 pairs with the smallest historical distance measure, in addition to the 20 pairs after the top 100 (pairs 101-120). This last set is valuable because most of the top pairs share certain characteristics..."

> "On the day following the last day of the pairs formation period, we begin to trade according to a pre-specified rule."

**Trading rule during 6-month period:**
1. Open position when prices diverge by 2σ
2. Close position at next price crossing
3. If no crossing by end of 6 months, close at last trading day
4. Positions can open/close multiple times

---

## ROLLING WINDOW / WALK-FORWARD STRUCTURE

**From page 13 (Section 2.3: Excess Return Computation):**

> "We initiate the pairs strategy by trading the pairs at the beginning of every month in the sample period, with the exception of the first twelve months, which are needed to estimate pairs for the strategy starting in the first month. The result is a time series of overlapping six-month trading period excess returns."

**Critical detail:**
- Formation periods: overlap with each other
- Trading periods: overlap with each other
- NOT strictly "Year 1 formation, Year 1 trading, Year 2 formation, Year 2 trading"
- Instead: formation and trading **both occur every month**, staggered

**From page 13 (continued):**

> "We correct for the correlation induced by overlap by averaging monthly returns across trading strategies that start one month apart as in Jegadeesh and Titman (1993). The resulting time series has the interpretation of the payoffs to a proprietary trading desk, which delegates the management of the six portfolios to six different traders whose formation and trading periods are staggered by one month."

**This means:**
- 6 different portfolios running simultaneously
- Each has its own 12-month formation
- Each has its own 6-month trading period
- They are staggered 1 month apart
- Results are averaged to eliminate overlap

---

## WHAT GATEV TESTS (To Understand Parameter Sensitivity)

### 1. Subperiod Analysis (Table 8)

The paper SPLITS the sample into two periods:
- **Pre-1989** (July 1963 - December 1988)
- **Post-1988** (January 1989 - December 2002)

**Result:** Raw returns drop 117bp/month → 38bp/month, but risk-adjusted returns persist.

**But:** This is NOT testing different formation/trading periods. This is testing temporal stability.

---

### 2. Sector-Neutral Pairs (Table 3)

Paper tests pairs trading within sectors:
- Utilities
- Transportation
- Financials
- Industrials

**Result:** Profitable in all sectors, not just utilities.

**But:** This is NOT testing different formation/trading periods. This is testing sector specificity.

---

### 3. Bootstrap Test (Table 6)

Paper creates random pairs sorted on prior 1-month performance.

**Result:** Random pairs have near-zero or negative returns. True pairs outperform.

**But:** This is NOT testing different formation/trading periods.

---

### 4. Robustness Tests (Section 3.9, Tables 9)

Paper tests:
- Using only top 3 deciles (large stocks)
- Short recalls on high volume days

**Result:** Profits persist.

**But:** These are NOT tests of formation/trading period variations.

---

## WHAT GATEV DOES NOT TEST

❌ **1-month formation, 1-month trading**
❌ **6-month formation, 6-month trading**
❌ **12-month formation, 3-month trading**
❌ **24-month formation, 12-month trading**

**The paper provides NO sensitivity analysis on formation/trading period length.**

---

## OUT-OF-SAMPLE VALIDATION (Important for Your Project)

**From page 5-6 (Section 1.2: Data Snooping and Market Response):**

> "One approach to the data snooping issue is to test the results out-of-sample. We completed and circulated the first draft of the working paper in 1999, using data through the end of 1998. The time lag between the first analysis and the present study gives us an ideal hold-out sample."

**Their out-of-sample test:**
- Original paper (1999): Data through 1998
- Present paper (2006): Uses 1999-2002 as hold-out OOS
- Used **exact same parameters** (12/6 formation/trading)
- Did NOT optimize for OOS period

**Result (page 6):**

> "Using the original model, but the post 1988 data, we found that over the 1999-2002 period, the excess return of the fully invested portfolio of the top twenty pairs averaged 10.4 percent per annum, with an annual standard deviation of 3.8% and a large and significant Newey-West-adjusted t-statistic of 4.82 – consistent with the long-term, in-sample results of our original analysis."

**Key quote:**

> "We were careful not to adjust our strategy from the first draft to the current draft of the paper, to avoid data-snooping criticisms."

---

## HOW TO JUSTIFY 12/6 FOR YOUR IMPLEMENTATION

### Option 1: Match Gatev Exactly (Weakest Justification)

**Reasoning:** "We follow Gatev et al. (2006) who use 12-month formation and 6-month trading periods for empirical testing."

**Problem:** Gatev admits this is arbitrary.

---

### Option 2: Economic Justification (Better)

**From your understanding of the mechanism:**

1. **Formation period (12 months):**
   - Sufficient data to estimate cointegration relationship reliably
   - Captures full market cycle (downturns, upturns, sideways)
   - Minimum ~250 trading days needed for stable estimates
   - Avoids short-term noise

2. **Trading period (6 months):**
   - Matches empirical convergence speed (~3.75 months average from Table 2)
   - Allows multiple round-trips per pair (~2 trades from Table 2)
   - Medium-term strategy (not day-trading, not long-term investing)
   - Reduces exposure to regime changes

---

### Option 3: Sensitivity Analysis (Best for Your Project)

**What you SHOULD do:**

```
Test alternative periods:
1. Formation: 6, 9, 12, 18, 24 months
2. Trading: 3, 6, 9, 12 months

Measure:
- PBO (Bailey validation)
- Out-of-sample Sharpe ratio
- Stability of results
- Number of signal trades

Report which period minimizes PBO
Report sensitivity table

Example:
Formation | Trading | PBO   | OOS Sharpe | # Trades
----------|---------|-------|------------|----------
6 months  | 3 months| 0.15  | 0.45       | 250
12 months | 6 months| 0.08  | 0.52       | 180
24 months | 12 months| 0.12  | 0.38       | 120
```

---

## SPECIFIC QUOTES ON WHY PARAMETERS MATTER

**From page 19-20 (Section 3.3: Transactions Costs):**

> "There is a second reason why our trading strategies require "too much" trading. We open pairs at any point during the trading period when the normalized prices diverge by two standard deviations. This is not a sensible rule towards the end of a trading interval."

This shows they RECOGNIZE that period length affects strategy efficiency.

---

## FOR YOUR DOCUMENTATION

### What to write in your CLAUDE.md:

❌ **DO NOT write:**
```
"Gatev (2006) established that 12-month formation 
and 6-month trading is optimal for pairs trading."
```

✅ **WRITE INSTEAD:**
```
"Gatev et al. (2006) use 12-month formation and 
6-month trading periods for their empirical tests. 
The authors explicitly note these periods were 
'chosen arbitrarily' (p.10). We follow this 
implementation for:

1. Empirical replication (matching published results)
2. Practical trading constraints:
   - 12 months sufficient for cointegration estimation
   - 6 months matches observed mean reversion period 
     (~3.75 months, Table 2)
   - Enables ~2 round-trips per pair within period
   
However, we note sensitivity analysis is warranted 
(see Bailey PBO validation framework)."
```

---

## CRITICAL INSIGHT: What Gatev Actually Tests

The **12/6 split is NOT a research finding** - it's a **design choice**.

Gatev's actual contributions:
1. ✅ Pairs trading is profitable (using 12/6 periods)
2. ✅ Profits persist out-of-sample (1999-2002)
3. ✅ Profits not from simple mean reversion
4. ✅ Profits not from bankruptcy risk
5. ✅ Profits persist across sectors
6. ✅ Profits survive transactions costs
7. ✅ Evidence of cointegration-based convergence

Gatev's NON-findings:
- ❌ Optimal formation period length
- ❌ Optimal trading period length
- ❌ Comparison of different period combinations
- ❌ Sensitivity to temporal parameters

---

## YOUR RESPONSIBILITY AS RESEARCHER

Since Gatev does NOT test period sensitivity, you should:

1. **Replicate Gatev first** (use 12/6) to establish baseline
2. **Then conduct sensitivity analysis** on period lengths
3. **Use Bailey PBO** to validate each combination
4. **Report all combinations tested** - don't hide alternatives
5. **Disclose which gives best PBO** - be transparent

This is the opposite of what led to vibecoding in your original CLAUDE.md.

---

## SUMMARY TABLE

| Aspect | What Gatev Says | What Gatev Tests | Your Responsibility |
|--------|-----------------|------------------|-------------------|
| Formation/Trading periods | Chosen "arbitrarily" | Only 12/6 split | Test alternatives |
| Optimality | NOT claimed | N/A | Conduct sensitivity analysis |
| Economic justification | None provided | N/A | Add rigorous reasoning |
| Out-of-sample validation | Provided (1999-2002) | Same 12/6 periods | Use Bailey PBO for validation |
| Parameter tuning | Avoided explicitly | N/A | Report all combinations tested |

---

## REFERENCES

- Gatev, E., Goetzmann, W.N., & Rouwenhorst, K.G. (2006). "Pairs Trading: Performance of a Relative Value Arbitrage Rule." Yale ICF Working Paper 08-03.
- Quote page numbers refer to SSRN version (bd7f5905-9512-4522-87ef-e551d3c2aea2)
- Tables referenced from paper directly

---

## FINAL NOTE

You were RIGHT to challenge the 1-year/1-year arbitrary choice. The Gatev paper itself admits it's arbitrary. This is exactly the kind of transparency that Bailey warns against losing when backtesting.

**Your job:** Make it not arbitrary through rigorous sensitivity analysis + Bailey validation.
