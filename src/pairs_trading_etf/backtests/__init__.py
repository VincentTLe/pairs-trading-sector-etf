"""
Backtesting Module for Pairs Trading
=====================================

This module provides a complete framework for backtesting cointegration-based
pairs trading strategies with proper validation.

Quick Start:
-----------
    >>> from pairs_trading_etf.backtests import load_config, run_walkforward_backtest
    >>> import pandas as pd
    >>>
    >>> # Load config and data
    >>> cfg = load_config('configs/experiments/optimal_180_90.yaml')
    >>> prices = pd.read_csv('data/raw/etf_prices_fresh.csv', index_col=0, parse_dates=True)
    >>>
    >>> # Run backtest
    >>> trades, summary = run_walkforward_backtest(prices, cfg, start_year=2010, end_year=2024)

Main Components:
---------------
- BacktestConfig: Unified configuration management
- run_walkforward_backtest: Walk-forward backtest engine
- run_validated_backtest: Full pipeline with CSCV validation (recommended)
- CSCV: Combinatorial Symmetric Cross-Validation for overfitting detection

Module Structure:
----------------
- engine.py: Main orchestration (run_walkforward_backtest, run_trading_simulation)
- pair_selection.py: Cointegration testing, pair selection, monitoring
- signal_generation.py: Z-score signals, stops, position sizing
- position_management.py: Position tracking, PnL, blacklisting
- pipeline.py: Validated backtest pipeline with CSCV
- metrics.py: Performance metrics and reporting

References:
----------
- Vidyamurthy, G. (2004). "Pairs Trading: Quantitative Methods and Analysis"
- Bailey et al. (2016). "The Probability of Backtest Overfitting"
"""

from .config import (
    BacktestConfig,
    load_config,
    merge_configs,
    get_conservative_config,
    get_aggressive_config,
    get_europe_only_config,
)

# Main engine - orchestration
from .engine import (
    run_trading_simulation,
    run_walkforward_backtest,
    estimate_kalman_hedge_ratio,
)

# Pair selection and cointegration
from .pair_selection import (
    run_engle_granger_test,
    select_pairs,
    monitor_cointegration_drift,
    update_hedge_ratio,
    calculate_snr,
    calculate_zero_crossing_rate,
    calculate_factor_correlation,
)

# Signal generation
from .signal_generation import (
    calculate_time_based_stop,
    check_vix_regime,
    calculate_volatility_adjusted_size,
    calculate_rolling_zscore,
    calculate_adaptive_lookback,
    generate_entry_signals,
    check_exit_conditions,
)

# Position management
from .position_management import (
    PairBlacklist,
    PositionManager,
    calculate_trade_pnl,
    calculate_position_sizes,
    create_trade_record,
    calculate_capital_per_trade,
    summarize_trades,
)

from .metrics import (
    calculate_performance_metrics,
    pnl_by_exit_reason,
    pnl_by_sector,
    print_backtest_report,
    save_results,
)

from .validation import (
    PurgedWalkForwardValidator,
    WalkForwardValidationResult,
)

# Validation Frameworks
# - CSCV: Combinatorial Symmetric Cross-Validation (Bailey et al. 2015) for PBO
# - WFA: Walk-Forward Analysis with purge/embargo (the correct validation approach)
from .cross_validation import (
    CSCVConfig,
    CSCVResult,
    CSCVAnalyzer,
    WalkForwardValidator,
    compare_cscv_vs_wfa,
    # Backward compatibility aliases
    CPCVConfig,
    CPCVResult,
    WalkForwardCPCV,
    compare_cscv_vs_cpcv,
)

# NOTE: cscv_backtest module is deprecated (depends on removed cross_validation.py)
# Use pipeline.py with cpcv_correct.py instead
# from .cscv_backtest import (
#     CSCVBacktestSplit,
#     ParameterGrid,
#     CSCVBacktestResult,
#     run_cscv_backtest,
#     validate_existing_backtest,
# )

from .pipeline import (
    PipelineConfig,
    PipelineResult,
    run_validated_backtest,
    quick_validate,
)

# fast_backtest.py has been removed - functionality merged into main engine

__all__ = [
    # Config
    "BacktestConfig",
    "load_config",
    "merge_configs",
    "get_conservative_config",
    "get_aggressive_config",
    "get_europe_only_config",
    # Engine - orchestration
    "run_trading_simulation",
    "run_walkforward_backtest",
    "estimate_kalman_hedge_ratio",
    # Pair Selection
    "run_engle_granger_test",
    "select_pairs",
    "monitor_cointegration_drift",
    "update_hedge_ratio",
    "calculate_snr",
    "calculate_zero_crossing_rate",
    "calculate_factor_correlation",
    # Signal Generation
    "calculate_time_based_stop",
    "check_vix_regime",
    "calculate_volatility_adjusted_size",
    "calculate_rolling_zscore",
    "calculate_adaptive_lookback",
    "generate_entry_signals",
    "check_exit_conditions",
    # Position Management
    "PairBlacklist",
    "PositionManager",
    "calculate_trade_pnl",
    "calculate_position_sizes",
    "create_trade_record",
    "calculate_capital_per_trade",
    "summarize_trades",
    # Metrics
    "calculate_performance_metrics",
    "pnl_by_exit_reason",
    "pnl_by_sector",
    "print_backtest_report",
    "save_results",
    # Validation helpers
    "PurgedWalkForwardValidator",
    "WalkForwardValidationResult",
    # Validation Frameworks (Bailey et al. 2015)
    "CSCVConfig",           # Config for CSCV analysis
    "CSCVResult",           # Result from CSCV/WFA analysis
    "CSCVAnalyzer",         # CSCV for PBO calculation (diagnostic)
    "WalkForwardValidator", # WFA with purge/embargo (correct validation)
    "compare_cscv_vs_wfa",  # Compare CSCV vs WFA results
    # Backward compatibility
    "CPCVConfig",
    "CPCVResult",
    "WalkForwardCPCV",
    "compare_cscv_vs_cpcv",
    # Integrated Pipeline (RECOMMENDED)
    "PipelineConfig",
    "PipelineResult",
    "run_validated_backtest",
    "quick_validate",
]
