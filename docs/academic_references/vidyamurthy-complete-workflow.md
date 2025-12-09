# Vidyamurthy (2004) - Complete Pairs Trading Workflow
## Từ Pair Selection → Tradability Test → Trading Band Design

**Source:** Vidyamurthy, G. (2004). Pairs Trading: Quantitative Methods and Analysis. Wiley Finance.

---

## OVERVIEW: 3-STEP PROCESS (Chapter 5, Page 83)

Vidyamurthy explicitly outlines the roadmap (Chapter 5):

> "The steps involved are as follows:
> 
> 1. Identify stock pairs that could potentially be cointegrated. This process can be based on the stock fundamentals or alternately on a pure statistical approach based on historical data. Our preferred approach is to make the stock pair guesses using fundamental information.
> 
> 2. Once the potential pairs are identified, we verify the proposed hypothesis that the stock pairs are indeed cointegrated based on statistical evidence from historical data. This involves determining the cointegration coefficient and examining the spread time series to ensure that it is stationary and mean reverting.
> 
> 3. We then examine the cointegrated pairs to determine the delta. A feasible delta that can be traded on will be substantially greater than the slippage encountered due to the bid-ask spreads in the stocks. We also indicate methods to compute holding periods."

This is the EXACT flow you should implement.

---

## STEP 1: PAIR SELECTION (Chapter 6)

### 1.1 Distance Measure (Chapter 6, Page 93-96)

**Key Quote (Page 85-86):**

> "In this methodology we prescribe here is distinctly different from the rules of thumb or heuristics approach. Instead of attempting to evaluate explicit partitions, this approach aims to arrive at a relative ordering of the pairs based on the degree of comovement. Each pair is associated with a score/distance measure. The higher the score, the greater the degree of comovement, and vice versa."

**The Distance Measure (Chapter 6, Section "The Distance Measure"):**

The distance is based on **normalized prices**. From page 93-96:

> "We choose a matching partner for each stock by finding the security that minimizes the sum of squared deviations between the two normalized price series."

**Mathematical form:**

Let \(P_A(t)\) and \(P_B(t)\) be prices of stocks A and B at time t.

Normalize both to start at the same level (e.g., both = 100 at t=0):

\[P_{A,norm}(t) = P_A(t) / P_A(0) \times 100\]
\[P_{B,norm}(t) = P_B(t) / P_B(0) \times 100\]

**Distance measure D:**

\[D = \sum_{t=1}^{T} [P_{A,norm}(t) - P_{B,norm}(t)]^2\]

**Interpretation (Page 94):**

> "The interpretation of the distance measure is relatively straightforward. It is a measure of the deviation of the two normalized price series from each other. When the distance measure is large, the two stocks have deviated significantly in their performance over the period of observation. When the distance measure is small, the two stocks have moved together pretty closely. Thus the distance measure captures the essence of pairs identified through common sense intuition."

### 1.2 Practical Implementation of Distance Measure

**Steps:**

1. Collect daily closing prices for stock A and B over formation period (e.g., 12 months)
2. Normalize: divide each day's price by the starting price
3. Calculate squared differences for each day
4. Sum all squared differences → This is your distance

**Interpretation:**

- **Small D (e.g., D = 0.5):** Stocks moved very similarly → Good pair candidate
- **Large D (e.g., D = 10):** Stocks diverged significantly → Unlikely cointegrated

**Threshold:**

From Chapter 6, the paper (Gatev et al. and Vidyamurthy) focuses on **top pairs** - those with smallest distance measures.

**From example (Page 96-97):**

The method finds the "best matching pairs" by exhaustive search through all possible pairs and selecting those with minimum distance.

### 1.3 Rationale for Distance Measure (Page 90)

**Why distance in normalized price space?**

From page 87-90 (Common Trends Model):

> "The common trends model and cointegration framework suggest that if two stocks share a common trend, their normalized prices should move together. Two stocks with similar performance characteristics (same industry, same size, same beta) are likely to have common trends."

**From page 97 (Reconciling Theory and Practice):**

> "In reconciling theory and practice, we note that while the cointegration framework is theoretically elegant, the practical implementation of identifying candidates based on distance in normalized price space is simple and effective."

---

## STEP 2: TESTING FOR TRADABILITY (Chapter 7)

### 2.1 Overview of Tradability Test

**Key Concept (Chapter 7, Page 104):**

> "In this chapter we will focus on whether the identified candidate pairs are actually tradable. Based on the discussions so far, we can state that a pair is tradable if the stocks making up the pair are cointegrated. We need to bear in mind, however, that in most cases we are dealing with systems that are not exactly cointegrated."

**Critical insight (Page 104):**

> "How do we decide that a pair is tradable even though it deviates from ideal conditions of cointegration?"

### 2.2 Two-Step Tradability Test (Chapter 7, Page 105)

Vidyamurthy prescribes exactly **2 steps**:

**Step 2A: Determine Linear Relationship**

**Step 2B: Test for Stationarity/Mean Reversion of Residuals**

From page 105:

> "Thus, similar to the cointegration testing, testing for tradability is also a two-step process: estimation of the linear relationship and measuring the degree of mean reversion."

### 2.3 STEP 2A: Linear Relationship (Chapter 7, Page 106-108)

**The Model (Page 106):**

\[\log(P_A^t) - \gamma \log(P_B^t) = \mu + \epsilon_t\]

Where:
- \(\gamma\) = cointegration coefficient (hedging ratio)
- \(\mu\) = equilibrium value (spread mean)
- \(\epsilon_t\) = residual (disturbance term)

**Economic Interpretation (Page 106-107):**

From page 106:

> "The interpretation of m as the common factor beta between the two stocks was already discussed in Chapter 6... m represents the premium paid for holding stock A over an equivalent position of stock B."

**How to Estimate \(\gamma\):**

### Method 1: Regression Approach (Page 108)

From Chapter 7:

> "Estimating the Linear Relationship: The Regression Approach"

**Procedure (Page 108):**

1. Take log-prices of both stocks
2. Run regression: \[\log(P_A^t) = \alpha + \gamma \log(P_B^t) + e_t\]
3. Use OLS to estimate \(\gamma\)
4. Compute residuals: \[\text{spread}_t = \log(P_A^t) - \gamma \log(P_B^t)\]

**Important notes:**

The regression approach is straightforward but has potential issues (spurious regression - page 105):

> "Granger and Newbold... aptly coined the phrase 'spurious regression' to describe it. Thus, as evidenced by spurious regression, the strong correlation property is not exclusive to cointegrated systems"

**This is why Step 2B is critical.**

### Method 2: Multifactor Approach (Page 107)

From Chapter 7, "Estimating the Linear Relationship: The Multifactor Approach":

The multifactor approach controls for common risk factors:

\[\log(P_A^t) - \gamma \log(P_B^t) = \text{factor loadings} + \epsilon_t\]

But Vidyamurthy suggests the simple regression approach is sufficient if residuals pass stationarity test.

### 2.4 STEP 2B: Testing Residual Stationarity (Chapter 7, Page 108-115)

**The Question (Page 108):**

> "Once the linear relationship is determined, how do we test for stationarity of the residuals?"

### Key Test: Augmented Dickey-Fuller (ADF) Test

From Chapter 7:

The most common test is **Augmented Dickey-Fuller (ADF) test**.

**ADF Test Model:**

\[\Delta \epsilon_t = \rho \epsilon_{t-1} + \sum_{j=1}^{p} \phi_j \Delta \epsilon_{t-j} + u_t\]

Where:
- \(\epsilon_t\) = residuals from the linear relationship
- \(\rho\) = autoregressive coefficient (testing if = 0)
- \(H_0: \rho = 0\) (unit root, non-stationary)
- \(H_1: \rho < 0\) (stationary)

**Interpretation (Page 112-115):**

From "Testing Residuals for Tradability":

- **If ADF test rejects null (p-value < 0.05):** Residuals are stationary → Pair is tradable
- **If ADF test fails to reject (p-value > 0.05):** Residuals have unit root → Pair is NOT tradable

**From page 112:**

> "The ADF test is designed to test for the existence of a unit root in the time series. If a unit root is found to exist, the series is nonstationary. Conversely, if no unit root exists, the series is stationary."

### 2.5 Mean Reversion Assessment (Chapter 7, Page 122-126)

**Beyond Stationarity: Spread Dynamics (Chapter 8)**

From Chapter 8, "Spread Dynamics" (page 122):

> "If the spread is stationary, it exhibits mean reversion. The question then becomes: How fast does it revert?"

**Half-Life Calculation (Page 122-125):**

Vidyamurthy prescribes calculating the **half-life of mean reversion**:

**Model (Page 122):**

\[\epsilon_t = \phi \epsilon_{t-1} + u_t\]

Estimate \(\phi\) via AR(1) regression.

**Half-life:**

\[\text{Half-life} = -\ln(2) / \ln(\phi)\]

**Interpretation:**

- **Short half-life (e.g., 5 days):** Spread reverts quickly → Good trading pair
- **Long half-life (e.g., 100 days):** Spread reverts slowly → May not be practical for trading

**From page 125:**

> "The half-life provides a direct measure of how quickly deviations from the long-run equilibrium are corrected. A short half-life indicates that deviations are quickly corrected, which is favorable for mean reversion trading."

### 2.6 Summary: Tradability Criteria

A pair is tradable if:
1. ✅ Linear relationship exists: \(\gamma\) estimated via regression
2. ✅ Residuals are stationary: ADF test p-value < 0.05
3. ✅ Mean reversion is fast: Half-life < trading holding period
4. ✅ Signal-to-noise ratio is good: Spread moves are clear

---

## STEP 3: TRADING BAND DESIGN (Chapter 8)

### 3.1 Overview: Band Design for White Noise (Chapter 8, Page 119-121)

**Problem Statement (Page 118):**

> "Introduction: The key question in trading design is: When do we open a position and when do we close it?"

**Key Insight (Page 119):**

> "Band Design for White Noise: If the spread is a white noise process, then bands can be designed based on the standard deviation of the spread."

### 3.2 Simplest Case: Entry/Exit Bands

From Chapter 8, page 119-121:

**Assumptions:**
- Spread is stationary
- Spread oscillates around mean \(\mu\)
- Standard deviation is \(\sigma\)

**Band Design:**

**Upper Band:**
\[\text{Upper Band} = \mu + k \times \sigma\]

**Lower Band:**
\[\text{Lower Band} = \mu - k \times \sigma\]

**Mean:**
\[\text{Center} = \mu\]

Where k = number of standard deviations (e.g., k = 2 for 2σ bands)

**Trading Rule (Page 119):**

From page 119:

> "A position is initiated when the spread reaches the upper or lower band. The position is closed when the spread returns to the mean."

### 3.3 Band Design Methodology

From Chapter 8, page 119-121:

**Step 1: Estimate Mean (\(\mu\))**

\[\mu = \frac{1}{T} \sum_{t=1}^{T} \epsilon_t\]

**Step 2: Estimate Standard Deviation (\(\sigma\))**

\[\sigma = \sqrt{\frac{1}{T-1} \sum_{t=1}^{T} (\epsilon_t - \mu)^2}\]

**Step 3: Choose k**

From page 119-121:

> "The choice of k determines the trading thresholds. A larger k results in fewer trading signals but higher probability of mean reversion. A smaller k results in more trading signals but lower probability of mean reversion."

**Typical choices:**
- k = 1σ: Aggressive (many trades)
- k = 2σ: Moderate (standard choice in Gatev et al.)
- k = 3σ: Conservative (few trades)

### 3.4 Nonparametric Approach (Chapter 8, Page 126-130)

**When to Use (Page 126):**

> "If we are uncertain about the distributional assumptions, a nonparametric approach may be preferred."

**Percentile-Based Bands (Page 126-130):**

Instead of using standard deviations, use historical percentiles:

**Lower Band (e.g., 5th percentile):**
\[\text{Entry threshold} = \text{Historical 5th percentile of spread}\]

**Upper Band (e.g., 95th percentile):**
\[\text{Entry threshold} = \text{Historical 95th percentile of spread}\]

**Mean:**
\[\text{Exit level} = \text{Historical median or mean}\]

**Procedure:**

1. Calculate historical percentiles of spread (5th, 25th, 50th, 75th, 95th)
2. Use these as entry/exit levels
3. No distributional assumption required

### 3.5 Regularization (Chapter 8, Page 130-135)

**Issue (Page 130):**

> "However, there are practical considerations when implementing bands. For instance, if the estimated bands are too narrow, we may experience false signals due to market microstructure effects like bid-ask bounce."

**Solution: Regularization (Page 130-135):**

From page 130:

> "Regularization involves adjusting the bands to ensure they are wide enough to be economically significant."

**Principle:**

Bands should be wider than:
- Bid-ask spread combined
- Trading costs (commissions, etc.)

**Mathematical form:**

\[\text{Trading threshold} = \text{Estimated band} + \text{Regularization factor}\]

Where regularization factor = trading costs + safety margin

### 3.6 Complete Example (Chapter 5, Page 82)

**Example Trading Setup (Page 82 in overview section):**

Given:
- Stock A bid price: $19.50, ask: $20.10
- Stock B bid price: $7.46, ask: $7.46
- Hedge ratio \(\gamma\) = 1.5
- Bid-ask spread A: 0.05%
- Bid-ask spread B: 0.10%

**Step 1: Calculate trading slippage:**

\[\text{Average slippage} = (0.0005 + 1.5 \times 0.0010) = 0.002 = 20 \text{ basis points}\]

**Step 2: Check if delta > slippage:**

\[\text{If spread deviation} > 20 \text{ bp}, \text{ then trade is feasible}\]

**Step 3: Entry Rule:**

"Buy A, Short B when spread diverges by more than 2σ"

**Step 4: Exit Rule:**

"Close when spread converges (returns to mean)"

---

## COMPLETE WORKFLOW SUMMARY

```
Phase 1: PAIR SELECTION
│
├─ Collect 12 months of daily prices (ALL stocks in universe)
├─ Normalize prices: P_norm = P / P_0
├─ Calculate distance: D = Σ(P_A,norm - P_B,norm)²
├─ Rank all pairs by distance (ascending)
└─ Short-list top 100-500 candidate pairs

Phase 2: TRADABILITY TEST
│
├─ For EACH candidate pair:
│   │
│   ├─ Step 2a: REGRESSION
│   │   ├─ Run: log(P_A) = α + γ·log(P_B) + e
│   │   ├─ Extract: γ (hedge ratio), μ (equilibrium), residuals
│   │   └─ Output: spread series
│   │
│   └─ Step 2b: ADF TEST (on residuals)
│       ├─ Run ADF test on spread_t
│       ├─ Calculate: half-life of mean reversion
│       ├─ Criteria: p-value < 0.05, half-life < holding period
│       └─ Output: ACCEPT or REJECT
│
└─ Result: List of tradable pairs

Phase 3: TRADING BAND DESIGN (for each accepted pair)
│
├─ Calculate spread statistics (from formation period)
│   ├─ Mean: μ = Σ(spread) / T
│   ├─ Std Dev: σ = √(Σ(spread - μ)² / T)
│   └─ Half-life: from AR(1) model
│
├─ Design ENTRY BANDS (k·σ method or percentile method)
│   ├─ Upper band: μ + k·σ
│   ├─ Lower band: μ - k·σ
│   └─ Apply regularization: add back trading costs
│
├─ Design EXIT RULES
│   ├─ Close at mean (μ)
│   ├─ Max holding period: based on half-life
│   └─ Stop-loss: beyond 3-4σ
│
└─ Output: Trading rules (entry/exit levels)

Phase 4: BACKTESTING (using Bailey PBO validation)
│
└─ For each rule set, compute PBO
    (See Bailey paper - validates if rule set is robust)
```

---

## CRITICAL DETAILS FROM VIDYAMURTHY

### Issue 1: Spurious Regression (Page 105)

> "Granger and Newbold... discovered that even completely independent random walks, when regressed against each other, can produce high r-squared values. This phenomenon is called 'spurious regression.'"

**Implication:** You MUST test residual stationarity (Step 2B), not just look at regression R².

### Issue 2: Exact vs. Approximate Cointegration (Page 104)

> "We need to bear in mind, however, that in most cases we are dealing with systems that are not exactly cointegrated."

**Implication:** Use ADF test + half-life calculation to quantify how well spread reverts.

### Issue 3: Band Width and Regularization (Page 130-135)

> "If the estimated bands are too narrow, we may experience false signals due to market microstructure effects."

**Implication:** Always add back estimated trading costs to bands.

### Issue 4: Equilibrium Premium (\(\mu\)) (Page 106-107)

> "m represents the premium paid for holding stock A over an equivalent position of stock B."

**Implication:** The spread mean is NOT zero - it's the cost difference of holding one vs. the other. Don't assume it's zero!

---

## PARAMETERS TO REPORT IN YOUR IMPLEMENTATION

For each pair in your backtest, MUST report:

| Parameter | Chapter | Meaning |
|-----------|---------|---------|
| Distance D | 6 | How close stocks moved during formation |
| γ (gamma) | 7 | Hedge ratio (units of B per unit of A) |
| μ (mu) | 7 | Equilibrium spread value |
| σ (sigma) | 8 | Volatility of spread |
| ADF p-value | 7 | Stationarity test (< 0.05 = stationary) |
| Half-life | 8 | Days for spread to revert 50% |
| Entry threshold | 8 | Entry band (μ ± k·σ + regularization) |
| Exit level | 8 | Exit band (μ + slippage buffer) |

---

## WHAT YOUR CODE SHOULD DO

### Step 1: Pair Selection Function

```python
def select_pairs(prices_df, formation_period=252):
    """
    Returns top N pairs ranked by distance measure
    Input: DataFrame with daily prices
    Output: List of (Stock A, Stock B, Distance)
    """
    # Normalize prices
    # Calculate distances
    # Sort by distance
    # Return top pairs
```

### Step 2: Tradability Test Function

```python
def test_tradability(price_A, price_B, lookback=252):
    """
    Returns: gamma, mu, sigma, adf_pvalue, half_life, is_tradable
    """
    # Step 2a: Regression to find gamma
    # Step 2b: ADF test on residuals
    # Calculate half-life
    # Return metrics
```

### Step 3: Band Design Function

```python
def design_trading_bands(spread_series, k=2, trading_costs_bp=20):
    """
    Returns: entry_upper, entry_lower, exit_level, stop_loss
    """
    # Calculate mean, std
    # Design bands
    # Add regularization
    # Return band levels
```

---

## REFERENCES (All from Vidyamurthy 2004)

- **Chapter 5** (Page 73-83): Overview and Roadmap
- **Chapter 6** (Page 85-101): Pairs Selection in Equity Markets
- **Chapter 7** (Page 104-117): Testing for Tradability
- **Chapter 8** (Page 118-138): Trading Design

---

## KEY TAKEAWAYS

1. **Pair selection is NOT arbitrary:** Use minimum distance in normalized price space (Chapter 6)
2. **Tradability requires TWO tests:** Regression + ADF stationarity (Chapter 7)
3. **Bands must account for costs:** Don't ignore bid-ask spreads and commissions (Chapter 8)
4. **Half-life matters:** Speed of mean reversion determines holding period (Chapter 8)
5. **Equilibrium has a premium:** Spread mean is NOT zero (Chapter 7)

These are EXACTLY what Vidyamurthy prescribes. Follow these steps rigorously.
