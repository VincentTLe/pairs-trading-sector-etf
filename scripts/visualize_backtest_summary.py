"""
Backtest Summary Visualization.

Creates comprehensive visualizations inspired by standard pairs trading analysis:
- Portfolio overview with cointegration heatmap
- Spread mean reversion plots
- Performance dashboard
- Trading signals visualization
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from pairs_trading_etf.backtests import run_walkforward_backtest, load_config
from pairs_trading_etf.visualization.backtest import (
    plot_cointegration_heatmap,
    plot_spread_mean_reversion,
    plot_zscore_with_signals,
    plot_performance_dashboard
)

OUTPUT_DIR = project_root / "results/figures"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def create_full_backtest_visualization(config_path, start_year=2010, end_year=2024):
    """
    Run backtest and create all visualizations.

    Parameters
    ----------
    config_path : str or Path
        Path to config YAML.
    start_year, end_year : int
        Year range.
    """
    print("\n" + "="*70)
    print("RUNNING BACKTEST WITH COMPREHENSIVE VISUALIZATION")
    print("="*70 + "\n")

    # Load config and data
    config_path = Path(config_path)
    config = load_config(str(config_path))

    # Resolve data path from config
    raw_path = getattr(config, 'price_data_path', 'data/raw/etf_prices_fresh.csv')
    prices_path = Path(raw_path)
    if not prices_path.is_absolute():
        prices_path = project_root / prices_path

    if not prices_path.exists():
        print(f"Error: Price data not found at {prices_path}")
        print("Please check 'price_data_path' in your config file.")
        return None, None
        
    prices = pd.read_csv(prices_path, index_col=0, parse_dates=True)

    print(f"Config: {config.experiment_name}")
    print(f"Price data: {len(prices)} days, {len(prices.columns)} ETFs")
    print(f"Backtest period: {start_year}-{end_year}\n")

    # Run backtest
    print("Running backtest...")
    trades_list, summary = run_walkforward_backtest(
        prices=prices,
        cfg=config,
        start_year=start_year,
        end_year=end_year
    )

    if len(trades_list) == 0:
        print("\nNo trades generated! Check configuration.")
        return None, None

    trades_df = pd.DataFrame(trades_list)

    print(f"\n✓ Backtest complete: {len(trades_df)} trades")
    print(f"  Total PnL: ${trades_df['pnl'].sum():+,.2f}")
    print(f"  Win Rate: {len(trades_df[trades_df['pnl'] > 0]) / len(trades_df) * 100:.1f}%\n")

    # Create visualizations
    print("="*70)
    print("GENERATING VISUALIZATIONS")
    print("="*70 + "\n")

    # 1. Performance Dashboard
    print("1. Creating performance dashboard...")
    plot_performance_dashboard(
        trades_df, 
        config.experiment_name,
        save_path=OUTPUT_DIR / f"dashboard_{config.experiment_name}.png"
    )

    # 2. Show top 3 winning trades with spread visualization
    print("\n2. Visualizing top 3 winning trades...")
    top_winners = trades_df.nlargest(3, 'pnl')

    for i, (idx, trade) in enumerate(top_winners.iterrows(), 1):
        pair = (trade['leg_x'], trade['leg_y'])
        print(f"\n   Win #{i}: {pair[0]}/{pair[1]} - ${trade['pnl']:+,.2f}")

        # Spread mean reversion plot
        plot_spread_mean_reversion(
            prices, pair, trade['hedge_ratio'],
            pd.to_datetime(trade['entry_date']),
            pd.to_datetime(trade['exit_date']),
            trade['pnl'],
            save_path=OUTPUT_DIR / f"spread_win_{i}_{pair[0]}_{pair[1]}.png"
        )

        # Z-score with signals
        plot_zscore_with_signals(
            prices, pair, trade['hedge_ratio'], trade.get('half_life', 30),
            pd.to_datetime(trade['entry_date']),
            pd.to_datetime(trade['exit_date']),
            entry_thresh=config.entry_threshold_sigma,
            exit_thresh=config.exit_threshold_sigma,
            stop_loss_thresh=config.stop_loss_sigma,
            save_path=OUTPUT_DIR / f"zscore_win_{i}_{pair[0]}_{pair[1]}.png"
        )

    # 3. Show top 3 losing trades
    print("\n3. Visualizing top 3 losing trades...")
    top_losers = trades_df.nsmallest(3, 'pnl')

    for i, (idx, trade) in enumerate(top_losers.iterrows(), 1):
        pair = (trade['leg_x'], trade['leg_y'])
        print(f"\n   Loss #{i}: {pair[0]}/{pair[1]} - ${trade['pnl']:+,.2f}")

        plot_spread_mean_reversion(
            prices, pair, trade['hedge_ratio'],
            pd.to_datetime(trade['entry_date']),
            pd.to_datetime(trade['exit_date']),
            trade['pnl'],
            save_path=OUTPUT_DIR / f"spread_loss_{i}_{pair[0]}_{pair[1]}.png"
        )

    print("\n" + "="*70)
    print("VISUALIZATION COMPLETE")
    print("="*70)
    print(f"\nAll figures saved to: {OUTPUT_DIR}")

    return trades_df, config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backtest Summary Visualization')
    parser.add_argument('--config', '-c', type=str,
                        default='configs/experiments/default.yaml',
                        help='Config file path')
    parser.add_argument('--start-year', type=int, default=2010)
    parser.add_argument('--end-year', type=int, default=2024)

    args = parser.parse_args()

    create_full_backtest_visualization(
        args.config,
        args.start_year,
        args.end_year
    )
