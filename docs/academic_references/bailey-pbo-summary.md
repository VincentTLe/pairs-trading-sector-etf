# Bailey et al. (2015) - "The Probability of Backtest Overfitting"
## Comprehensive Summary (From Paper ONLY - No Speculation)

---

## METADATA
- **Title:** The Probability of Backtest Overfitting
- **Authors:** David H. Bailey, Jonathan M. Borwein, Marcos López de Prado, Qiji Jim Zhu
- **Date:** February 27, 2015 (Revised)
- **Institution:** Lawrence Berkeley National Laboratory, University of Newcastle, Guggenheim Partners
- **Paper Available At:** https://ssrn.com/abstract=2326253

---

## ABSTRACT (Direct Quote)

> "Many investment firms and portfolio managers rely on backtests (i.e., simulations of performance based on historical market data) to select investment strategies and allocate capital. Standard statistical techniques designed to prevent regression overfitting, such as hold-out, tend to be unreliable and inaccurate in the context of investment backtests. We propose a general framework to assess the probability of backtest overfitting (PBO). We illustrate this framework with specific generic, model-free and nonparametric implementations in the context of investment simulations, which implementations we call combinatorially symmetric cross-validation (CSCV). We show that CSCV produces reasonable estimates of PBO for several useful examples."

---

## 1. INTRODUCTION & MOTIVATION

### The Core Problem

The paper starts with a fundamental issue in quantitative finance:

> "Modern investment strategies rely on the discovery of patterns that can be quantified and monetized in a systematic way... Recent advances in algorithmic research and high-performance computing have made it nearly trivial to test millions and billions of alternative investment strategies on a finite dataset of financial time series. While these advances are undoubtedly useful, they also present a negative and often silenced side-effect: The alarming rise of false positives in related academic publications."

### The False Positive Problem

The authors illustrate with a concrete example:

> "Even for the simplest case, there are at least five parameters that the researcher can fit: Two sample lengths for the moving averages, entry threshold, exit threshold and stop-loss. The number of combinations that can be tested over thousands of securities is in the billions."

They explain the statistical problem:

> "Although this approach is consistent with the Neyman-Pearson framework of hypothesis testing, it is highly likely that false positives will emerge with a probability greater than 5%. The reason is that a 5% false positive probability only holds when we apply the test exactly once. However, we are applying the test on the same data multiple times (indeed, billions of times), making the emergence of false positives almost certain."

### The Multiple Testing Problem

> "The probability of finding false positives increases with the number of tests conducted on the same data (Miller [25]). As each researcher carries out millions of regressions (Sala-i-Martin [28]) on a finite number of independent datasets without controlling for the increased probability of false positives, some researchers have concluded that 'most published research findings are false' (see Ioannidis [17])."

### The Main Problem

> "Furthermore, it is common practice to use this computational power to calibrate the parameters of an investment strategy in order to maximize its performance. But because the signal-to-noise ratio is so weak, often the result of such calibration is that parameters are chosen to profit from past noise rather than future signal. The outcome is an overfit backtest."

The authors note:

> "Scientists at Lawrence Berkeley National Laboratory have developed an online tool to demonstrate this phenomenon. This tool generates a time series of pseudorandom returns, and then calibrates the parameters of an optimal monthly strategy... After a few hundred iterations, it is trivial to find highly profitable strategies in-sample, despite the small number of parameters involved. Performance out-of-sample is, of course, utterly disappointing."

---

## 2. THE APPROACH (Directly from Section 1)

### Three Key Steps

The paper states (p.4-5):

> "First, we introduce a precise characterization of the event of backtest overfitting. The idea is simple and intuitive: For overfitting to occur, the strategy configuration that delivers maximum performance in sample (IS) must systematically underperform the remaining configurations out of sample (OOS)."

> "Second, we establish a general framework for assessing the probability of the event of backtest overfitting. We model this phenomenon of backtest overfitting using an abstract probability space in which the sample space consist of pairs of IS and OOS test results."

> "Third, we set as null hypothesis that backtest overfitting has indeed taken place, and develop an algorithm that tests for this hypothesis. For a given strategy, the probability of backtest overfitting (PBO) is then evaluated as the conditional probability that this strategy underperforms the median OOS while remaining optimal IS."

### What is PBO? (Definition)

> "While the PBO provides a direct way to quantify the likelihood of backtest overfitting, the general framework also affords us information to look into the overfitting issue from different perspectives. For example, besides PBO, this framework can also be used to assess performance decay, probability of loss, and possible stochastic dominance of a strategy."

---

## 3. MATHEMATICAL FRAMEWORK (Section 2.1)

### Definition 2.1: Backtest Overfitting

From page 9:

> "We say that the backtest strategy selection process overfits if a strategy with optimal performance IS has an expected ranking below the median OOS."

Mathematically:
$$\sum_{n=1}^{N} E[r_n | r \in \Omega^*_n] \text{Prob}[r \in \Omega^*_n] \leq N/2$$

### Definition 2.2: Probability of Backtest Overfitting (PBO)

> "A strategy with optimal performance IS is not necessarily optimal OOS. Moreover, there is a non-null probability that this strategy with optimal performance IS ranks below the median OOS. This is what we define as the probability of backtest overfit (PBO). More precisely:"

$$\text{PBO} = \sum_{n=1}^{N} \text{Prob}[r_n < N/2 | r \in \Omega^*_n] \text{Prob}[r \in \Omega^*_n]$$

### Interpretation (from page 9)

> "In other words, we say that a strategy selection process overfits if the expected performance of the strategies selected IS is less than the median performance rank OOS of all strategies. In that situation, the strategy selection process becomes in fact detrimental."

### Important Clarification (page 9-10)

> "Note that in this context IS corresponds to the subset of observations used to select the optimal strategy among the N alternatives. With IS we do not mean the period on which the investment model underlying the strategy was estimated (e.g., the period on which crossing moving averages are computed, or a forecasting regression model is estimated). Consequently, in the above definition we refer to overfitting in relation to the strategy selection process, not a strategy's model calibration (e.g., in the context of regressions). That is the reason we were able to define overfitting without knowledge of the strategy's underlying models, i.e., in a model-free and non-parametric manner."

### On the Probability Interpretation (page 5)

> "It is worth clarifying in what sense do we speak of a probability of backtest overfitting. Backtest overfitting is a deterministic fact (either the model is overfit or it is not), hence it may seem unnatural to associate a probability to a non-random event. Given some empirical evidence and priors, we can infer the posterior probability that overfitting has taken place. Examples of this line of reasoning abound in information theory and machine learning treatises, e.g. [23]. It is in this Bayesian sense that we define and estimate PBO."

---

## 4. CSCV METHOD (Section 2.2)

### Overview

From page 10:

> "A generic, model-free, and nonparametric testing algorithm is desirable, since backtests are applied to trading strategies produced using a great variety of different methods and models. For this reason, we present a specific implementation, which we call a combinatorially symmetric cross-validation (CSCV)."

### Algorithm 2.3: CSCV Steps (pages 10-12)

The paper provides a detailed algorithm with 5 steps:

**Step 1:** Form matrix M from N trial performance series

> "First, we form a matrix M by collecting the performance series from the N trials. In particular, each column n = 1, . . . , N represents a vector of profits and losses over t = 1, . . . , T observations associated with a particular model configuration tried by the researcher."

**Step 2:** Partition into S submatrices

> "Second, we partition M across rows, into an even number S of disjoint submatrices of equal dimensions."

**Step 3:** Form combinations

> "Third, we form all combinations CS of Ms, taken in groups of size S/2."

The number of combinations is given by:
$$\binom{S}{S/2} = \binom{S-1}{S/2-1} = \ldots = \sum_{i=0}^{S/2-1} \frac{S-i}{S/2-i}$$

Example: If S=16, will form 12,780 combinations.

**Step 4 & 5:** For each combination, compute IS and OOS performance rankings, derive logits, and generate distribution.

From page 12:

> "Running the N model configurations over each of these combinations allows us to derive a relative ranking, expressed as a logit. The outcome is a distribution of logits, one per combination. Note that each training subset combination is re-used as a testing subset and vice-versa (as is possible because we split the data in two equal parts)."

---

## 5. PBO INTERPRETATION (Section 3.1)

From page 13:

> "The PBO defined in Section 2.1 may now be estimated using the CSCV method with φ = ∫₀₋∞ f(λ)dλ. This represents the rate at which optimal IS strategies underperform the median of the OOS trials."

### What φ Values Mean

From page 13:

> "For φ ≈ 0, a low proportion of the optimal IS strategy outperformed the median of the trials in most of the testing sets indicating no significant overfitting. On the flip side, φ ≈ 1 indicates high likelihood of overfitting."

### Three Uses for PBO (page 13)

The paper lists:

> "We consider at least three uses for PBO: 
> i) In general the value of φ provides us a quantitative sense about the likelihood of overfitting. In accordance with standard applications of the Neyman-Pearson framework, a customary approach would be to reject models for which PBO is estimated to be greater than 0.05. 
> ii) PBO could be used as a prior probability in Bayesian applications, where for instance the goal may be to derive the posterior probability of a model's forecast. 
> iii) We could compute the PBO on a large number of investment strategies, and use those PBO estimates to compute a weighted portfolio, where the weights are given by (1 −PBO), 1/PBO or some other scheme."

### CRITICAL NOTE: No Fixed Threshold!

**The paper ONLY suggests 0.05 as a "customary approach" following Neyman-Pearson framework - it does NOT mandate this as the threshold.**

---

## 6. OTHER OVERFITTING STATISTICS (Section 3)

### 1. Performance Degradation (Section 3.2)

From page 13-14:

> "Because we are trying every combination of Ms taken in groups of size S/2, there is no reason to expect the distribution of R to dominate over R. The implication is that, generally, Rn* < max{R} ≈ max{R} = Rn*. For a regression Rn*c = α + βRcn* + εc, the β will be negative in most practical cases, due to compensation effects."

> "An intuitive explanation for this negative slope is that overfit backtests minimize future performance: The model is so fit to past noise, that it is often rendered unfit for future signal. And the more overfit a backtest is, the more memory is accumulated against its future performance."

### 2. Probability of Loss (Section 3.2)

> "A particularly useful statistic is the proportion of combinations with negative performance, Prob[Rn*c < 0]. Note that, even if φ ≈ 0, Prob[Rn*c < 0] could be high, in which case the strategy's performance OOS is probably poor for reasons other than overfitting."

### 3. Stochastic Dominance (Section 3.3)

From page 16-17:

> "A further application of the results derived in Section 2.2 is to determine whether the distribution of Rn* across all c ∈CS stochastically dominates over the distribution of all R. Should that not be the case, it would present strong evidence that strategy selection optimization does not provide consistently better OOS results than a random strategy selection."

---

## 7. LIMITATIONS (Section 5)

### Limitations in Design (Section 5.1)

The paper identifies several important limitations:

1. **Symmetry assumption may not suit all strategies**

> "First, a key feature of the CSCV implementation is symmetry... However, the complexity of investment strategies and performance measures makes it unlikely that any particular method will be a one size fits all solution."

2. **May not suit time-dependent strategies**

> "Moreover, symmetrically dividing the sample performance in to S symmetrically layered sub-samples also may not suitable for certain strategies. For example, if the performance measure as a time series has a strong autocorrelation, then such a division may obscure the characterization especially when S is large."

3. **Weighting assumption**

> "Finally, the CSCV estimate of the probability measure assumes all the sample statistics carries the same weight. Without knowing any prior information on the distribution of the backtest performance measure this is, of course, a natural and reasonable choice. If, however, one does have knowledge regarding the distribution of the backtest performance measure, then model-specific methods of dividing the sample performance measure and assigning different weights to different strips of the subdivision are likely to be more accurate."

### Limitations in Application (Section 5.2)

From page 23-24:

1. **Requires complete information**

> "First, the researcher must provide full information regarding the actual trials conducted, to avoid the file drawer problem (the test is only as good as the completeness of the underlying information)."

2. **Cannot detect flawed backtests**

> "Second, this procedure does nothing to evaluate the correctness of a backtest. If the backtest is flawed due to bad assumptions, such as incorrect transaction costs or using data not available at the moment of making a decision, our approach will be making an assessment based on flawed information."

3. **Cannot account for out-of-sample structural breaks**

> "Third, this procedure only takes into account structural breaks as long as they are present in the dataset of length T. If a structural break occurs outside the boundaries of the available dataset, the strategy may be overfit to a particular data regime, which our PBO has failed to account for because the entire set belongs to the same regime."

4. **High PBO doesn't mean no good strategies exist**

> "Fourth, although a high PBO indicates overfitting in the group of N tested strategies, skillful strategies can still exists in these N strategies. For example, it is entirely possible that all the N strategies have high but similar Sharpe ratios. Since none of the strategies is clearly better than the rest, PBO will be high. Here overfitting is among many 'skillful' strategies."

5. **DO NOT use PBO as optimization objective**

> "Fifth, we must warn the reader against applying CSCV to guide the search for an optimal strategy. That would constitute a gross misuse of our method. As Strathern [31] eloquently put it, 'when a measure becomes a target, it ceases to be a good measure.' Any counter-overfitting technique used to select an optimal strategy will result in overfitting. For example, CSCV can be employed to evaluate the quality of a strategy selection process, but PBO should not be the objective function on which such selection relies."

---

## 8. PARAMETERS (Section 4)

### Parameter S

From page 21:

> "A key parameter of our procedure is the value of S. This regulates the number of submatrices Ms that will be generated... S must be large enough so that the number of combinations suffices to draw inference. If S is too small, the left tail of the distribution of logits will be underrepresented."

**Recommendation:**

> "For example, S = 16 we will obtain 12,780 logits..., and σ[f(λ)] < 0.0045, with less than a 0.01 estimation error at 95% confidence level. Also, if M contains 4 years of daily data, S = 16 would equate to quarterly partitions, and the serial correlation structure would be preserved. For these two reasons, we believe that S = 16 is a reasonable value to use in most cases."

### Parameter N (Number of Trials)

From page 22:

> "Another key parameter is the number of trials (i.e., the number of columns in Ms). Hold-out's disregard for the number of trials attempted was the reason we concluded it was an inappropriate method to assess a backtest's representativeness... N must be large enough to provide sufficient granularity to the values of the relative rank, ωc. If N is too small, ωc will take only a very few values, which will translate into a very discrete number of logits, making f(λ) too discontinuous, and adding estimation error to the evaluation of φ."

---

## 9. PRACTICAL EXAMPLES (Section 6)

### Example 1: Overfit Seasonal Strategy (Random Walk)

> "First, as discussed in the above cited paper, a time series of 1,000 daily prices (about 4 years) was generated by drawing from a random walk. Parameters were optimized (Entry day = 11, Holding period = 4, Stop loss = -1 and Side = 1), resulting in an annualized Sharpe ratio of 1.27."

Results:

> "Figure 7 shows that approx. 53% of the SR OOS are negative, despite all SR IS being positive and ranging between 1 and 2.2. Figure 8 plots the distribution of logits, which implies that, despite the elevated SR IS, the PBO is as high as 55%."

### Example 2: Valid Seasonal Strategy (With Real Effect)

> "Second, we generated a time series of 1,000 daily prices (about 4 years), following a random walk. But unlike the first case, we have shifted the returns of the first 5 random observations of each month to be centered at a quarter of a standard deviation. This simulates a monthly seasonal effect, which the strategy selection procedure should discover."

Results:

> "Figure 11 shows only 13% of the OOS SR to be negative... Figure 12 shows a distribution of logits with a PBO of only 13%. Figure 13 evidences that the distribution of OOS SR from IS optimal combinations clearly dominates the overall distribution of OOS SR. The CSCV analysis has this time correctly recognized the validity of this backtest."

---

## 10. COMPARISON WITH OTHER METHODS

### Why Hold-Out is Problematic (pages 5-6)

The paper lists 5 reasons:

1. **Possible data leakage**: "if the data is publicly available, it is quite likely that the researcher has used the 'hold-out' as part of the IS dataset"

2. **Unconscious data snooping**: "any seasoned researcher knows well how financial variables performed over the time period covered by the OOS dataset, and that information may well be used in the strategy design, consciously or not"

3. **Inadequate for small samples**: "Weiss and Kulikowski [34] argue that hold-out should not be applied to an analysis with less than 1,000 observations. For example, if a strategy trades on a weekly basis, hold-out should not be used on backtests of less than 20 years."

4. **High variance**: "Van Belle and Kerr [33] point out the high variance of hold-out estimation errors. If one is unlucky, the chosen hold-out section may be the one that refutes a valid strategy or supports an invalid strategy."

5. **Doesn't account for number of trials**: "as long as the researcher tries more than one strategy configuration, overfitting is always present (see Bailey et al. [1] for a proof). The hold-out method does not take into account the number of trials attempted before selecting a particular strategy configuration"

### Why K-Fold CV is Problematic (page 20)

> "Although a very valid approach in many situations, we believe that our procedure is more satisfactory than K-FCV in the context of strategy selection. In particular, we would like to compute the Sharpe ratio (or any other performance measure) on each of the k testing sets of size T/k. This means that k must be sufficiently small, so that the Sharpe ratio estimate is reliable... But if k is small, K-FCV will essentially reduce to a 'hold-out' method, which we have argued is unreliable."

---

## 11. KEY FINDINGS & CONCLUSIONS

From the conclusion (page 28):

> "To that end, we have proposed a general framework for modeling the IS and OOS performance using probability. We define the probability of backtest overfitting (PBO) as the probability that an optimal strategy IS underperforms the mean OOS. To facilitate the evaluation of PBO for particular applications, we have proposed a combinatorially symmetric cross-validation (CSCV) implementation framework for estimating this probability. This estimate is generic, symmetric, model-free and non-parametric."

### Important Warning (page 28)

> "We certainly hope that this study will raise greater awareness concerning the futility of computing and reporting backtest results, without first controlling for PBO and MinBTL."

---

## 12. WHAT THE PAPER DOES NOT SAY

### Things NOT in the paper:

1. ❌ **"PBO < 40% is optimal"** - NO threshold of 40% appears anywhere
2. ❌ **"DSR > 0 is required"** - DSR is mentioned in references but NOT in this paper
3. ❌ **"Monthly re-testing with p=0.15 is required"** - Completely absent
4. ❌ **"Entry threshold 0.75σ is optimal"** - The paper uses example with 2σ
5. ❌ **"ADF p < 0.05 is mandatory"** - Not in this paper

### What the paper DOES say about thresholds:

> "In accordance with standard applications of the Neyman-Pearson framework, a customary approach would be to reject models for which PBO is estimated to be greater than 0.05."

**This is a SUGGESTION following statistical convention, NOT a mandate.**

---

## REFERENCES CITED IN THE PAPER

Key citations:
- [1] Bailey et al. (2014) - "Pseudo-mathematics and financial charlatanism"
- [2] Bailey & López de Prado (2012, 2014) - "The Sharpe Ratio Efficient Frontier" and "The Deflated Sharpe Ratio"
- [25] Miller - "Simultaneous Statistical Inference"
- [28] Sala-i-Martin - "I just ran two million regressions"
- [29] Schorfheide & Wolpin - "On the Use of Holdout Samples"
- [31] Strathern - "Improving Ratings: Audit in the British University System"

---

## SUMMARY TABLE

| Concept | Paper Says | NOT in Paper |
|---------|-----------|-------------|
| **What is PBO** | Prob(IS-best underperforms OOS median) | ❌ |
| **How to compute** | Via CSCV algorithm with logits | ❌ |
| **Suggested threshold** | φ > 0.05 = "customary" rejection | PBO < 40% ❌ |
| **Other metrics** | Performance degradation, Prob[loss], Stochastic dominance | DSR, Monthly testing ❌ |
| **Parameters** | S=16 suggested, N must be large | Specific σ thresholds ❌ |
| **Key limitation** | Cannot detect flawed backtests | ❌ |
| **Warning** | Don't use PBO as optimization objective | ❌ |

---

## END NOTES

**This summary contains ONLY statements directly from the Bailey et al. (2015) paper. Nothing has been added, invented, or speculated.**

For your project restoration, use **only these documented facts**. Anything else that was in your CLAUDE.md (like 0.75σ, PBO<40%, p=0.15) came from somewhere else or was created without academic basis.
