# Comprehensive Codebase Audit Report
**Date:** 2025-12-08
**Project:** Pairs Trading ETF Backtest System
**Status:** Pre-Cleanup Analysis

---

## Executive Summary

Codebase health: **6/10** - Functional research code with accumulated technical debt

**Critical Findings:**
1. 🚨 **Bug #13** - Stop-loss parameter not working (CRITICAL)
2. 🚨 **Hardcoded parameters** inconsistent across modules (HIGH)
3. 🚨 **Code duplication** - Kalman filter implemented twice (HIGH)
4. ⚠️ **Over-complex functions** - `engine.py` has 700-line function (HIGH)
5. ⚠️ **Config sprawl** - 45 YAML files, need consolidation (MEDIUM)

**Removable code:** ~1,000 lines (8.5% of codebase)

---

## 1. Critical Bugs

### Bug #13: Stop-Loss Parameter Not Working ❌
- **File:** `src/pairs_trading_etf/backtests/engine.py`
- **Status:** NOT FIXED
- **Impact:** CRITICAL - Cannot test stop-loss strategies
- **Evidence:** Configs with `stop_loss_sigma: 5.0` and `99.0` produce identical PnL
- **Root cause:** Suspected config parameter not being read correctly
- **Line:** ~1406 (stop-loss logic in trading simulation)

**Test case that fails:**
```python
config_a.stop_loss_sigma = 5.0   # Tight stop
config_b.stop_loss_sigma = 99.0  # Effectively disabled

run_backtest(config_a) → PnL: $1,061
run_backtest(config_b) → PnL: $1,061  # IDENTICAL! ❌
```

**Action:** Add debug logging to verify config value propagation

---

## 2. Hardcoded Parameters (CRITICAL INCONSISTENCIES)

### 2.1 Correlation Thresholds MISMATCH

| File | Parameter | Value | Issue |
|------|-----------|-------|-------|
| **pair_generation.py:102** | `min_corr` | 0.60 | ❌ TOO LOW |
| **pair_generation.py:103** | `max_corr` | 0.99 | ❌ TOO HIGH |
| **config.py:62** | `min_correlation` | 0.75 | ✅ Config |
| **config.py:63** | `max_correlation` | 0.95 | ✅ Config |

**IMPACT:** May select pairs with correlation 0.60-0.74 (BELOW config threshold!)

### 2.2 Half-Life Bounds MISMATCH

| File | Parameter | Value | Issue |
|------|-----------|-------|-------|
| **engine.py:631** | `min_half_life` | 5.0 | ❌ WRONG |
| **engine.py:632** | `max_half_life` | 30.0 | ❌ WRONG |
| **config.py:55** | `min_half_life` | 2.0 | ✅ Config |
| **config.py:56** | `max_half_life` | 50.0 | ✅ Config |

**IMPACT:** Filters out pairs with HL 2-4.9 and 30.1-50 (config ALLOWS these!)

### 2.3 Magic Numbers Without Constants

**engine.py** - Multiple hardcoded values:
- Line 59: `if len(spread) < 30:` - Minimum observations (repeated 4x)
- Line 115: `crossings * (252 / n_days)` - Trading days per year
- Line 213: `max(effective_stop, 1.5)` - Minimum stop-loss floor
- Line 1201: `abs(delta_nonparam - delta_white) / delta_white > 0.2` - 20% disagreement threshold
- Line 2001: `len(formation_prices) < cfg.formation_days * 0.8` - 80% minimum data

**cpcv_correct.py** - Risk thresholds:
- Lines 124-128: PBO risk levels (0.20, 0.40, 0.60)
- Line 135: Overfitting threshold (0.40)

**pipeline.py** - Validation gates:
- Line 673: `degradation_ratio > 0.5` - 50% degradation
- Line 679: `rank_correlation < 0.3` - 30% rank threshold

---

## 3. Code Duplication

### 3.1 Kalman Filter (DUPLICATE IMPLEMENTATION)

**Location 1:** `backtests/engine.py` lines 236-400 (164 lines)
```python
def estimate_kalman_hedge_ratio(px, py, ...):
    # Full Kalman filter implementation
```

**Location 2:** `features/kalman_hedge.py` (373 lines total)
```python
def kalman_filter_hedge(px, py, ...):
    # Full Kalman filter implementation with regime detection
```

**Issue:** COMPLETE DUPLICATION - Same functionality in two places
**Impact:** Maintenance nightmare, potential divergence
**Action:** DELETE from engine.py, import from features module

### 3.2 Minimum Observations Check (REPEATED 4x)

```python
# Repeated in engine.py:
if len(spread) < 30:  # Lines 59, 98, 148
    return 0.0
```

**Action:** Extract to named constant `MIN_OBSERVATIONS_FOR_STATS = 30`

---

## 4. Over-Complex Functions

### 4.1 CRITICAL: `run_trading_simulation()` - 700 LINES!

**File:** `backtests/engine.py` lines 1200-1900
**Length:** ~700 lines in single function
**Cyclomatic complexity:** VERY HIGH
**Responsibilities:**
- Entry signal generation
- Exit condition checking
- Position tracking
- PnL calculation
- Cointegration monitoring
- VIX-based position scaling
- Blacklist management
- Logging and diagnostics

**Recommendation:** Break into smaller functions:
```python
def run_trading_simulation():
    # Main orchestration
    for t in range(len(trading_prices)):
        check_entry_signals(...)
        check_exit_conditions(...)
        execute_trades(...)
        update_tracking(...)
```

### 4.2 `select_pairs()` - 450 LINES

**File:** `backtests/engine.py` lines 700-1150
**Length:** ~450 lines
**Responsibilities:**
- Cointegration testing
- SNR/ZCR calculation
- Pair scoring and filtering
- Optimal threshold calculation
- Ranking and selection

**Recommendation:** Extract to separate module `pair_selection.py`

### 4.3 `run_validated_backtest()` - 400 LINES

**File:** `backtests/pipeline.py` lines 309-707
**Length:** ~400 lines
**Recommendation:** Extract validation logic to helper functions

---

## 5. Unused/Redundant Code

### 5.1 COMPLETELY UNUSED Modules

| File | Lines | Status | Action |
|------|-------|--------|--------|
| `cscv_backtest.py` | ? | DEPRECATED (broken) | 🗑️ DELETE |
| `analysis/cointegration/johansen.py` | 201 | Not imported | 📦 Archive |
| `pipelines/johansen_scan.py` | 137 | Not imported | 📦 Archive |
| `pipelines/pair_scan.py` | 498 | Superseded | 📦 Archive |

**Total removable:** ~850+ lines

### 5.2 Empty/Placeholder Modules

- `cointegration/__init__.py` - Only docstring, no exports
- **Action:** Either populate or remove

---

## 6. Config File Chaos

### 6.1 Config Inventory

**Total:** 45 YAML files

**Active (19 files):**
- Core (3): `default.yaml`, `vidyamurthy_practical.yaml`, `vidyamurthy_optimal.yaml`
- CPCV (3): `cpcv_core.yaml`, `cpcv_quality.yaml`, `cpcv_highspeed.yaml`
- Phase 4 (4): `phase4_a/b/c/global.yaml`
- Analysis (6): `optimal_180_90.yaml`, `quick_backtest.yaml`, etc.
- Legacy (3): `v17_dynamic_holding.yaml`, etc.

**Archived (12 files):** Properly moved to `archive/`

**Deleted but uncommitted (14 files):**
- `v14_vidyamurthy_full.yaml`
- `v15b_vix_volsizing.yaml`
- `v16_optimized.yaml`
- `v16b_best.yaml`
- `v17a_best.yaml`
- `v17a_vol_filter.yaml`
- `v17b_dynamic_balanced.yaml`
- `v17b_dynamic_exit.yaml`
- `v17c_combined.yaml`
- `v17d_slow_conv.yaml`
- `v17e_slow_conv_60.yaml`
- `v17s.yaml`
- `v18_lit_quality.yaml`
- `v18_snr_zcr_conservative.yaml`

### 6.2 Config Issues

1. **No clear naming convention** - Mix of descriptive + version numbers
2. **Redundancy** - `optimal_180_90.yaml` vs `*_no_monitoring.yaml` differ in 1 param
3. **Missing documentation** - Many configs lack `description:` field

**Recommendation:** Keep only 5-7 core configs, archive rest

---

## 7. Module Organization Issues

### 7.1 Structure Assessment

**Good:**
- ✅ Clear separation: `data/`, `features/`, `backtests/`, `pipelines/`
- ✅ Proper `__init__.py` exports
- ✅ Type hints used consistently
- ✅ No circular dependencies

**Issues:**

#### Inconsistent Module Depth
```
analysis/
├── correlation.py           # Depth 2
└── cointegration/
    └── johansen.py         # Depth 3 (not exported)
```

#### Overlapping Functionality
- Cointegration testing in TWO places:
  - `cointegration/engle_granger.py` (used)
  - `analysis/cointegration/johansen.py` (unused)

#### Unclear Boundaries
- `engine.py` contains SNR/ZCR calculations (should be in `features/`)
- Kalman hedge in both `engine.py` AND `features/kalman_hedge.py`

---

## 8. Documentation Issues

### 8.1 Missing Parameter Justification

| Parameter | Value | Documented? | Source |
|-----------|-------|-------------|--------|
| `entry_threshold_sigma` | 0.75 | ✅ YES | Vidyamurthy Ch.8 |
| `exit_threshold_sigma` | 0.0 | ✅ YES | Mean reversion theory |
| `stop_loss_sigma` | 4.0 | ❌ NO | Unknown! |
| `max_holding_days` | 60 | ❌ NO | Why 60? |
| `stop_tightening_rate` | 0.15 | ❌ NO | Why 15%? |
| `adaptive_lookback_multiplier` | 4.0 | ✅ YES | QMA practice |
| `min_spread_range_pct` | 0.02 | ❌ NO | Why 2%? |

**Action:** Document ALL parameters with academic/practical justification

### 8.2 Missing Docstrings

Private functions without docstrings:
- `data/global_universe.py`: `_normalize_tickers()`, `_resolve_categories()`
- `backtests/pipeline.py`: `_generate_config_variations()`, `_build_returns_matrix()`

---

## 9. Code Quality Metrics

### Lines of Code by Module

| Module | Lines | Status |
|--------|-------|--------|
| `backtests/engine.py` | 2,074 | 🔴 CRITICAL - Too large |
| `backtests/cpcv_correct.py` | 950 | 🟡 HIGH |
| `backtests/pipeline.py` | 836 | 🟡 HIGH |
| `backtests/config.py` | 738 | 🟢 OK |
| `backtests/validation.py` | 733 | 🟢 OK |
| Other files | <500 | 🟢 OK |

### Code Health Scorecard

| Category | Score | Status |
|----------|-------|--------|
| **Module Organization** | 7/10 | Good structure, some overlap |
| **Code Clarity** | 5/10 | Too many magic numbers |
| **Function Complexity** | 4/10 | Several 400+ line functions |
| **Documentation** | 7/10 | Good docstrings, missing param docs |
| **DRY Compliance** | 5/10 | Duplicate Kalman, repeated constants |
| **Config Management** | 6/10 | Too many configs, needs organization |

**Overall Health: 6/10** - Functional but needs cleanup

---

## 10. Cleanup Action Plan

### Phase 1: CRITICAL (Do First)

1. **Fix Bug #13** - Stop-loss parameter
   - Add debug logging
   - Test config propagation
   - Verify fix with extreme values

2. **Remove duplicate Kalman**
   - Delete from `engine.py` lines 236-400
   - Import from `features.kalman_hedge`

3. **Fix hardcoded parameters**
   - `pair_generation.py`: Use config correlation bounds
   - `engine.py`: Use config half-life bounds

### Phase 2: CODE CLEANUP

4. **Create `constants.py`**
   - Extract all magic numbers
   - Document source/justification for each

5. **Refactor `engine.py`**
   - Break `run_trading_simulation()` into functions
   - Extract `select_pairs()` to separate module

6. **Delete unused code**
   - Remove `cscv_backtest.py`
   - Archive Johansen modules

### Phase 3: CONFIG CONSOLIDATION

7. **Archive experimental configs**
   - Keep only 5-7 core configs
   - Move rest to `archive/`

8. **Create new `default.yaml`**
   - All parameters justified
   - Based on `constants.py`
   - Clear documentation

9. **Commit deleted configs**
   - Clean git status
   - Document archival reason

### Phase 4: TESTING

10. **Run full backtest suite**
    - Verify no regressions
    - Check Bug #13 fixed
    - Validate parameter consistency

---

## 11. Estimated Effort

| Phase | Tasks | Effort | Priority |
|-------|-------|--------|----------|
| Phase 1 | Fix bugs, remove duplication | 4 hours | CRITICAL |
| Phase 2 | Code cleanup, refactoring | 8 hours | HIGH |
| Phase 3 | Config consolidation | 2 hours | MEDIUM |
| Phase 4 | Testing | 2 hours | HIGH |
| **Total** | | **16 hours** | |

---

## 12. Success Criteria

After cleanup, codebase should have:

✅ No critical bugs
✅ No hardcoded parameters (all in constants.py)
✅ No code duplication
✅ Functions < 200 lines
✅ <= 7 active config files
✅ All parameters documented with source
✅ Code health score: 8/10+

---

*Generated: 2025-12-08*
*Status: AWAITING CLEANUP*
*Next: Begin Phase 1 - Critical Fixes*
