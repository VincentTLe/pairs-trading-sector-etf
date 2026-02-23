# Vidyamurthy Implementation: Code-Level Details
## Exactly What Code Must Do for Each Step (Chapter-by-Chapter)

---

## PART I: DATA PREPARATION

### Input Requirements (from PDF)
```
Daily price data:
├─ Closing prices (adjusted for splits/dividends)
├─ High resolution: ≥ 250 trading days per period
├─ Continuity: No gaps longer than 1 week
└─ Universe: 3-5 pairs (can expand to 50+ for real trading)

Data quality checks:
├─ No negative prices
├─ No zero-volume days (unless entire market closed)
├─ Returns normally distributed (roughly)
└─ Stationarity NOT required for raw prices (that's what we test!)
```

### Code Template
```python
import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import adfuller

def load_and_clean_data(symbols, start_date='2015-01-01', end_date='2024-12-31'):
    """
    Vidyamurthy Chapter 2: Time Series basics
    Input: List of ETF symbols
    Output: DataFrame with log prices
    """
    prices_df = pd.DataFrame()
    
    for sym in symbols:
        # Load from Yahoo Finance
        data = yf.download(sym, start=start_date, end=end_date, progress=False)
        
        # Log-transform for returns analysis
        prices_df[sym] = np.log(data['Adj Close'])
    
    # Check for missing data
    assert prices_df.isnull().sum().sum() == 0, "Missing data detected"
    
    # Sanity check: prices should be increasing generally
    returns = prices_df.diff().dropna()
    assert returns.std() > 0, "Zero volatility detected"
    
    return prices_df, returns

# Usage
prices, returns = load_and_clean_data(['XLY', 'XLV', 'XLE', 'XLI', 'XLF'])
print(f"Data loaded: {prices.shape[0]} days, {prices.shape[1]} assets")
print(f"Avg daily return: {returns.mean().mean()*100:.3f}%")
```

---

## PART II: PAIR SELECTION (Chapter 6)

### Step 1: Correlation Screening
```python
def screen_by_correlation(prices_df, min_corr=0.80):
    """
    Vidyamurthy Chapter 6, Page 85:
    "Initial screening will use correlation; pairs with correlation > 0.80..."
    
    Input: DataFrame of log prices
    Output: List of (symbol_A, symbol_B, corr) tuples
    """
    returns = prices_df.diff().dropna()
    corr_matrix = returns.corr()
    
    candidate_pairs = []
    
    # Iterate through upper triangle (avoid duplicates)
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            sym_a = corr_matrix.columns[i]
            sym_b = corr_matrix.columns[j]
            corr_ab = corr_matrix.iloc[i, j]
            
            if abs(corr_ab) > min_corr:  # Absolute value to catch negative corr too
                candidate_pairs.append((sym_a, sym_b, abs(corr_ab)))
    
    # Sort by correlation (best first)
    candidate_pairs.sort(key=lambda x: x[2], reverse=True)
    
    print(f"Found {len(candidate_pairs)} pairs with |correlation| > {min_corr}")
    for sym_a, sym_b, corr in candidate_pairs[:5]:
        print(f"  {sym_a:5} vs {sym_b:5}: {corr:.4f}")
    
    return candidate_pairs

# Usage
pairs = screen_by_correlation(prices, min_corr=0.80)
```

### Step 2: Distance Measure (Critical!)
```python
def calculate_distance_measure(prices_a, prices_b, lookback_days=252):
    """
    Vidyamurthy Chapter 6, Page 93-96:
    "The distance is based on normalized prices."
    
    Formula: D = Σ[P_A,norm(t) - P_B,norm(t)]²
    
    Input: Two price series (log prices, same length)
    Output: Single distance number
    """
    # Ensure same length
    assert len(prices_a) == len(prices_b), "Price series must be same length"
    
    # Normalize: P_norm = P / P_0 × 100
    pa_norm = prices_a / prices_a.iloc[0] * 100
    pb_norm = prices_b / prices_b.iloc[0] * 100
    
    # Calculate sum of squared deviations
    distance = np.sum((pa_norm - pb_norm)**2)
    
    return distance, pa_norm, pb_norm

def rank_pairs_by_distance(prices_df, candidate_pairs, lookback_days=252):
    """
    Score all candidate pairs
    Input: candidate_pairs from screen_by_correlation
    Output: Ranked list with distance scores
    """
    ranked = []
    
    # Use last N days for distance calculation
    prices_recent = prices_df.iloc[-lookback_days:].reset_index(drop=True)
    
    for sym_a, sym_b, corr in candidate_pairs:
        distance, _, _ = calculate_distance_measure(
            prices_recent[sym_a], 
            prices_recent[sym_b]
        )
        
        ranked.append({
            'pair': (sym_a, sym_b),
            'correlation': corr,
            'distance': distance,
            'normalized_distance': distance / lookback_days  # Per day average
        })
    
    # Sort by distance (LOWER is better - less deviation)
    ranked.sort(key=lambda x: x['distance'])
    
    print(f"Top 10 pairs by distance (lower = better comovement):")
    for i, entry in enumerate(ranked[:10], 1):
        print(f"  {i}. {entry['pair'][0]}-{entry['pair'][1]}: "
              f"distance={entry['distance']:.1f}, corr={entry['correlation']:.4f}")
    
    return ranked

# Usage
ranked_pairs = rank_pairs_by_distance(prices, pairs)
```

---

## PART III: TESTING FOR TRADABILITY (Chapter 7)

### Step 2a: Estimate Linear Relationship (Regression)

```python
def estimate_linear_relationship(price_a, price_b, lookback_days=252):
    """
    Vidyamurthy Chapter 7, Page 108:
    "Estimating the Linear Relationship: The Regression Approach"
    
    Model: log(P_A) = α + γ·log(P_B) + ε
    
    Input: Two price series
    Output: gamma (hedge ratio), alpha, residuals, R²
    
    Note: MUST use recent lookback period for this!
    """
    from scipy import stats
    
    # Use log prices as-is
    x = price_b.values
    y = price_a.values
    
    # OLS regression: y = alpha + gamma*x + residual
    # Using np.polyfit or scipy.stats.linregress
    gamma, alpha, r_value, p_value, std_err = stats.linregress(x, y)
    
    residuals = y - (alpha + gamma * x)
    
    r_squared = r_value ** 2
    
    return {
        'gamma': gamma,          # Hedge ratio (slope)
        'alpha': alpha,          # Intercept
        'residuals': residuals,  # ε_t = log(P_A) - γ·log(P_B) - α
        'r_squared': r_squared,
        'p_value': p_value,
        'std_error': std_err
    }

# Usage example
recent_prices = prices.iloc[-252:]
sym_a, sym_b = 'XLY', 'XLV'
result = estimate_linear_relationship(
    recent_prices[sym_a],
    recent_prices[sym_b]
)
print(f"Hedge ratio γ = {result['gamma']:.4f}")
print(f"R² = {result['r_squared']:.4f}")
print(f"Residuals std = {result['residuals'].std():.4f}")
```

### Step 2b: Test Residual Stationarity (ADF Test)

```python
def test_residual_stationarity(residuals):
    """
    Vidyamurthy Chapter 7, Page 108-115:
    "Testing Residuals for Tradability"
    
    ADF Test: H0 = unit root (non-stationary)
    Reject H0 if p-value < 0.05 → Residuals are stationary
    
    Input: Residual time series
    Output: ADF test results
    """
    from statsmodels.tsa.stattools import adfuller
    
    result = adfuller(residuals, autolag='AIC')
    
    return {
        'test_statistic': result[0],
        'p_value': result[1],
        'n_lags': result[2],
        'n_obs': result[3],
        'critical_values': result[4],
        'ic_best': result[5],
        'is_stationary': result[1] < 0.05  # This is the key boolean!
    }

# Usage
residuals = result['residuals']
adf_result = test_residual_stationarity(residuals)
print(f"ADF p-value: {adf_result['p_value']:.4f}")
print(f"Stationary? {adf_result['is_stationary']}")

if adf_result['p_value'] < 0.05:
    print("✓ Pair is stationary - TRADABLE")
else:
    print("✗ Pair has unit root - NOT TRADABLE")
```

### Step 2c: Calculate Half-Life of Mean Reversion

```python
def calculate_half_life(residuals):
    """
    Vidyamurthy Chapter 8, Page 122-125:
    "Half-Life Calculation"
    
    Model: ε_t = φ·ε_{t-1} + u_t (AR(1))
    Half-life: τ = -ln(2) / ln(φ)
    
    Input: Residual time series
    Output: Half-life in trading days
    """
    from scipy.optimize import minimize
    
    # AR(1) model: ε_t = φ·ε_{t-1} + u_t
    # Fit using OLS on lagged residuals
    
    n = len(residuals)
    
    # Create lagged matrix
    y = residuals[1:]          # ε_t
    x = residuals[:-1]         # ε_{t-1}
    
    # OLS: phi = covariance(ε_t, ε_{t-1}) / variance(ε_{t-1})
    phi = np.cov(y, x)[0, 1] / np.var(x)
    
    # Check if phi > 1 (non-mean-reverting)
    if phi >= 1:
        return float('inf')  # No mean reversion
    
    # Half-life
    half_life_days = -np.log(2) / np.log(phi)
    
    return half_life_days, phi

# Usage
half_life, phi = calculate_half_life(result['residuals'])
print(f"AR(1) coefficient φ = {phi:.4f}")
print(f"Half-life = {half_life:.1f} trading days ({half_life/252*365:.1f} calendar days)")
```

### Full Tradability Check Function

```python
def check_tradability(prices_a, prices_b, lookback_days=252):
    """
    COMPLETE TRADABILITY TEST (Vidyamurthy Chapter 7)
    
    Returns: Dictionary with all test results
    """
    # Ensure log prices
    if prices_a.iloc[0] < 0:
        prices_a = np.exp(prices_a)  # Already log
    
    # Step 2a: Estimate linear relationship
    reg_result = estimate_linear_relationship(prices_a, prices_b)
    gamma = reg_result['gamma']
    residuals = reg_result['residuals']
    
    # Critical Check 1: Avoid spurious regression
    if reg_result['r_squared'] < 0.70:
        print(f"Warning: Low R² = {reg_result['r_squared']:.3f} - may be spurious")
    
    # Step 2b: ADF test
    adf_result = test_residual_stationarity(residuals)
    
    # Step 2c: Half-life
    half_life, phi = calculate_half_life(residuals)
    
    # FINAL DECISION
    is_tradable = (
        adf_result['is_stationary'] and  # Must be stationary
        half_life < 252 and              # Half-life < 1 year (necessary for 6-mo trades)
        phi > 0 and phi < 1              # Valid mean-reversion AR coeff
    )
    
    return {
        'gamma': gamma,
        'r_squared': reg_result['r_squared'],
        'residuals': residuals,
        'adf_pvalue': adf_result['p_value'],
        'is_stationary': adf_result['is_stationary'],
        'phi': phi,
        'half_life_days': half_life,
        'is_tradable': is_tradable,
        'summary': (
            f"Tradable: {is_tradable} | "
            f"ADF p={adf_result['p_value']:.3f} | "
            f"HL={half_life:.0f} days | "
            f"γ={gamma:.4f}"
        )
    }

# Usage
for sym_a, sym_b, _ in ranked_pairs[:3]:
    print(f"\nTesting {sym_a}-{sym_b}...")
    result = check_tradability(
        prices.iloc[-252:][sym_a],
        prices.iloc[-252:][sym_b]
    )
    print(result['summary'])
```

---

## PART IV: TRADING BAND DESIGN (Chapter 8)

### Calculate Spread Statistics

```python
def calculate_spread_statistics(residuals):
    """
    Vidyamurthy Chapter 8, Page 119-121:
    "Band Design for White Noise"
    
    Input: Residuals from regression
    Output: Mean, std, percentiles
    """
    spread = residuals
    
    stats = {
        'mean': np.mean(spread),
        'std': np.std(spread),
        'median': np.median(spread),
        'min': np.min(spread),
        'max': np.max(spread),
        'percentile_5': np.percentile(spread, 5),
        'percentile_25': np.percentile(spread, 25),
        'percentile_75': np.percentile(spread, 75),
        'percentile_95': np.percentile(spread, 95),
    }
    
    return spread, stats

# Usage
spread, spread_stats = calculate_spread_statistics(residuals)
print(f"Spread mean: {spread_stats['mean']:.4f}")
print(f"Spread std:  {spread_stats['std']:.4f}")
print(f"Spread range: [{spread_stats['min']:.4f}, {spread_stats['max']:.4f}]")
```

### Design Trading Bands

```python
def design_trading_bands(residuals, k_sigma=2.0, method='parametric'):
    """
    Vidyamurthy Chapter 8, Page 119-130:
    
    Method 1 (Parametric): Bands = μ ± k·σ
    Method 2 (Nonparametric): Bands = percentiles
    
    Input: 
      - residuals (from formation period)
      - k_sigma: Number of std devs (1.5, 2.0, 2.5)
      - method: 'parametric' or 'nonparametric'
    
    Output: Entry/exit band levels
    """
    spread, stats = calculate_spread_statistics(residuals)
    
    if method == 'parametric':
        # Entry: when spread deviates by k_sigma std devs
        entry_upper = stats['mean'] + k_sigma * stats['std']
        entry_lower = stats['mean'] - k_sigma * stats['std']
        
        # Exit: when spread returns toward mean (0.5σ threshold)
        exit_level = stats['mean']
        
        bands = {
            'entry_upper': entry_upper,
            'entry_lower': entry_lower,
            'exit_level': exit_level,
            'method': f'Parametric (k={k_sigma}σ)',
            'description': 'Entry on divergence, exit at mean'
        }
    
    elif method == 'nonparametric':
        # Use historical percentiles
        entry_upper = stats['percentile_95']
        entry_lower = stats['percentile_5']
        exit_level = stats['median']
        
        bands = {
            'entry_upper': entry_upper,
            'entry_lower': entry_lower,
            'exit_level': exit_level,
            'method': 'Nonparametric (5th/95th percentile)',
            'description': 'No distributional assumption'
        }
    
    return bands, stats

# Usage
bands_para, stats = design_trading_bands(residuals, k_sigma=2.0, method='parametric')
bands_nonpara, _ = design_trading_bands(residuals, method='nonparametric')

print(f"Parametric bands (k=2σ):")
print(f"  Entry upper: {bands_para['entry_upper']:.4f}")
print(f"  Entry lower: {bands_para['entry_lower']:.4f}")
print(f"  Exit level:  {bands_para['exit_level']:.4f}")

print(f"\nNonparametric bands:")
print(f"  Entry upper: {bands_nonpara['entry_upper']:.4f}")
print(f"  Entry lower: {bands_nonpara['entry_lower']:.4f}")
print(f"  Exit level:  {bands_nonpara['exit_level']:.4f}")
```

### Apply Regularization (Add Back Trading Costs)

```python
def apply_regularization(bands, gamma, bid_ask_cost_bps=3, slippage_bps=1):
    """
    Vidyamurthy Chapter 8, Page 130-135:
    "Regularization: Adjusting the bands to ensure they are wide enough"
    
    Don't enter if spread move is smaller than trading costs!
    
    Input:
      - bands: From design_trading_bands()
      - gamma: Hedge ratio (controls position ratio)
      - bid_ask_cost_bps: Round-trip bid-ask (both legs)
      - slippage_bps: Market impact + execution delay
    
    Output: Adjusted bands
    """
    total_cost_bps = bid_ask_cost_bps + slippage_bps
    total_cost_dollars = total_cost_bps / 10000  # Convert to decimal
    
    # Adjust: spreads smaller than costs won't be profitable
    bands_adjusted = bands.copy()
    
    # Widen entry bands by cost amount (to ensure profit potential)
    bands_adjusted['entry_upper'] += total_cost_dollars
    bands_adjusted['entry_lower'] -= total_cost_dollars
    
    # Move exit slightly to guarantee > cost recovery
    bands_adjusted['exit_level'] = bands['exit_level'] + total_cost_dollars / 2
    
    return bands_adjusted

# Usage
bands_final = apply_regularization(
    bands_para, 
    gamma=1.5,
    bid_ask_cost_bps=3,
    slippage_bps=1
)

print(f"Regularized bands (including {3+1} bps costs):")
print(f"  Entry upper: {bands_final['entry_upper']:.4f}")
print(f"  Entry lower: {bands_final['entry_lower']:.4f}")
print(f"  Exit level:  {bands_final['exit_level']:.4f}")
```

---

## PUTTING IT ALL TOGETHER: Complete Pair Selection Function

```python
def vidyamurthy_complete_pair_selection(prices_df, lookback_days=252):
    """
    ONE FUNCTION: Do all of Chapters 6-8
    
    Input: DataFrame of log prices
    Output: Tradable pairs with fixed trading rules
    """
    tradable_pairs = []
    
    # Step 1: Correlation screening
    pairs = screen_by_correlation(prices_df.iloc[-lookback_days:], min_corr=0.80)
    
    # Step 2: Rank by distance
    ranked = rank_pairs_by_distance(prices_df.iloc[-lookback_days:], pairs)
    
    # Step 3: Check tradability & design bands for each
    for pair_dict in ranked:
        sym_a, sym_b = pair_dict['pair']
        recent_prices = prices_df.iloc[-lookback_days:]
        
        # Test tradability
        trad = check_tradability(recent_prices[sym_a], recent_prices[sym_b])
        
        if trad['is_tradable']:
            # Design bands
            bands, stats = design_trading_bands(trad['residuals'], k_sigma=2.0)
            bands_final = apply_regularization(bands, gamma=trad['gamma'])
            
            tradable_pairs.append({
                'pair': (sym_a, sym_b),
                'gamma': trad['gamma'],
                'half_life_days': trad['half_life_days'],
                'adf_pvalue': trad['adf_pvalue'],
                'spread_mean': stats['mean'],
                'spread_std': stats['std'],
                'entry_upper': bands_final['entry_upper'],
                'entry_lower': bands_final['entry_lower'],
                'exit_level': bands_final['exit_level'],
                'max_hold_days': int(2 * trad['half_life_days']),
                'residuals': trad['residuals']
            })
    
    print(f"\n{'='*70}")
    print(f"VIDYAMURTHY TRADABILITY TEST RESULTS")
    print(f"{'='*70}")
    print(f"Total candidate pairs: {len(ranked)}")
    print(f"Tradable pairs: {len(tradable_pairs)}")
    print(f"\nTradable pairs (ready for walk-forward backtest):")
    
    for p in tradable_pairs:
        print(f"\n  {p['pair'][0]}-{p['pair'][1]}:")
        print(f"    Hedge ratio γ        = {p['gamma']:.4f}")
        print(f"    Half-life            = {p['half_life_days']:.0f} days")
        print(f"    ADF p-value          = {p['adf_pvalue']:.3f}")
        print(f"    Entry bands          = [{p['entry_lower']:.4f}, {p['entry_upper']:.4f}]")
        print(f"    Exit level           = {p['exit_level']:.4f}")
        print(f"    Max hold period      = {p['max_hold_days']} days")
    
    return tradable_pairs

# USAGE - RUN ONCE TO GET FIXED TRADING RULES
tradable_pairs = vidyamurthy_complete_pair_selection(prices.iloc[-252:])

# Save these for the walk-forward backtest
import pickle
with open('tradable_pairs_formation_2015_2016.pkl', 'wb') as f:
    pickle.dump(tradable_pairs, f)

print("\n✓ Saved tradable pairs rules. DO NOT MODIFY THESE FOR BACKTEST!")
```

---

## KEY POINTS FOR IMPLEMENTATION

1. **Formation Period is ONE-TIME**
   - Calculate γ, μ, σ, bands from [2015-01-01 to 2016-01-01]
   - FREEZE these values
   - Use for entire 2016-2024 trading period

2. **Log Prices**
   - Always use log(price) in regression
   - Spread = log(P_A) - γ·log(P_B) (not dollar differences)

3. **ADF Test is Critical**
   - p-value < 0.05 means stationary (good)
   - p-value > 0.05 means non-stationary (reject pair)

4. **Half-Life Controls Holding Period**
   - If HL = 30 days, max hold = 60 days
   - Don't hold beyond that (reversion window closed)

5. **Regularization is Not Optional**
   - Add back bid-ask costs to bands
   - Otherwise entry signals lose money on execution

---

**Next step:** Walk-forward backtest using these FIXED rules. 🚀
