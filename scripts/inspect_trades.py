"""
Trade Inspection Tool.

Allows deep-dive inspection of specific trades from a backtest result.
Uses shared visualization logic for consistency.

Usage:
    python scripts/inspect_trades.py --best-worst 3
    python scripts/inspect_trades.py --year 2022
    python scripts/inspect_trades.py --pair XLF XLI
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys
import yaml
import argparse

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from pairs_trading_etf.visualization.backtest import visualize_trade_enhanced

# Default paths
DATA_PATH = project_root / "data/raw/etf_prices_fresh.csv"
OUTPUT_DIR = project_root / "results/figures"
OUTPUT_DIR.mkdir(exist_ok=True)

ETF_METADATA_PATH = project_root / "configs/etf_metadata.yaml"


def load_etf_sectors():
    """Load ETF to sector mapping"""
    if not ETF_METADATA_PATH.exists():
        return {}
    with open(ETF_METADATA_PATH, 'r') as f:
        metadata = yaml.safe_load(f)
    
    etf_to_sector = {}
    for sector, etfs in metadata.get('sectors', {}).items():
        for etf in etfs:
            etf_to_sector[etf] = sector
    return etf_to_sector


def load_config_thresholds(trades_path):
    """Load entry/exit thresholds from config_snapshot.yaml in same folder as trades.csv"""
    trades_path = Path(trades_path)
    config_path = trades_path.parent / "config_snapshot.yaml"
    
    defaults = {
        'entry_threshold_sigma': 2.0,
        'exit_threshold_sigma': 0.5,
        'stop_loss_sigma': 4.0,
        'zscore_lookback': 60
    }
    
    if not config_path.exists():
        return defaults
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return {
            'entry_threshold_sigma': config.get('entry_threshold_sigma', defaults['entry_threshold_sigma']),
            'exit_threshold_sigma': config.get('exit_threshold_sigma', defaults['exit_threshold_sigma']),
            'stop_loss_sigma': config.get('stop_loss_sigma', defaults['stop_loss_sigma']),
            'zscore_lookback': config.get('zscore_lookback', defaults['zscore_lookback'])
        }
    except Exception:
        return defaults


def find_latest_trades_file():
    """Find most recent trades file from results"""
    results_dir = project_root / "results"
    
    # Look for timestamped folders
    timestamped = sorted(results_dir.glob("2025-*"), reverse=True)
    for folder in timestamped:
        trades_file = folder / "trades.csv"
        if trades_file.exists():
            return trades_file
            
    return None


def get_data_path_from_config(trades_path):
    """Try to find data path from config_snapshot.yaml"""
    if trades_path is None:
        return None
        
    trades_path = Path(trades_path)
    config_path = trades_path.parent / "config_snapshot.yaml"
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config.get('price_data_path')
        except Exception:
            pass
    return None


def load_data(trades_path=None, config_override=None):
    """
    Load price data and trades.
    Priority for data path:
    1. --config argument (if provided)
    2. config_snapshot.yaml in trades folder
    3. Default (data/raw/etf_prices_fresh.csv)
    """
    # Determine trades path first
    if trades_path is None:
        trades_path = find_latest_trades_file()
        if trades_path is None:
            raise FileNotFoundError("Could not find any trades.csv in results/")
    else:
        trades_path = Path(trades_path)
    
    print(f"Loading trades from: {trades_path}")
    trades = pd.read_csv(trades_path, parse_dates=['entry_date', 'exit_date'])

    # Determine data path
    relative_data_path = None
    
    if config_override:
        # 1. Explicit config arg
        with open(config_override, 'r') as f:
            cfg = yaml.safe_load(f)
        relative_data_path = cfg.get('price_data_path')
        print(f"Using data path from config argument: {relative_data_path}")
    
    if not relative_data_path:
        # 2. Config snapshot
        relative_data_path = get_data_path_from_config(trades_path)
        if relative_data_path:
            print(f"Using data path from snapshot: {relative_data_path}")

    # 3. Default
    if not relative_data_path:
        relative_data_path = "data/raw/etf_prices_fresh.csv"
        print(f"Using default data path: {relative_data_path}")

    # Resolve absolute path
    data_path = Path(relative_data_path)
    if not data_path.is_absolute():
        data_path = project_root / data_path
        
    if not data_path.exists():
        raise FileNotFoundError(f"Price data not found at {data_path}")

    print(f"Loading prices from: {data_path}")
    prices = pd.read_csv(data_path, index_col=0, parse_dates=True)
    
    return prices, trades, trades_path


def list_trades_summary(trades, path):
    """Print summary table of all trades"""
    print(f"\n{'='*80}")
    print(f"TRADES SUMMARY from {path}")
    print(f"{'='*80}")
    
    # Summary stats
    print(f"\nTotal trades: {len(trades)}")
    winners = len(trades[trades['pnl'] > 0])
    print(f"Winners: {winners} ({winners/len(trades)*100:.1f}%)")
    print(f"Total PnL: ${trades['pnl'].sum():,.2f}")
    
    # By exit reason
    if 'exit_reason' in trades.columns:
        print("\nBy Exit Reason:")
        for reason in trades['exit_reason'].unique():
            subset = trades[trades['exit_reason'] == reason]
            print(f"  {reason}: {len(subset)} trades, ${subset['pnl'].sum():+,.2f}")
    
    # Top 10 trades
    print(f"\n{'='*80}")
    print("TOP 10 TRADES BY PnL:")
    print(f"{'='*80}")
    
    top10 = trades.nlargest(10, 'pnl')[['leg_x', 'leg_y', 'entry_date', 'pnl', 'exit_reason']]
    if not top10.empty:
        top10['entry_date'] = pd.to_datetime(top10['entry_date']).dt.strftime('%Y-%m-%d')
        print(top10.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Trade Inspection Tool')
    parser.add_argument('--trades', '-t', type=str, default=None,
                        help='Path to trades CSV file (default: latest)')
    parser.add_argument('--best-worst', '-bw', type=int, default=None,
                        help='Show N best and N worst trades')
    parser.add_argument('--year', '-y', type=int, default=None,
                        help='Show trades for specific year')
    parser.add_argument('--pair', '-p', nargs=2, default=None,
                        help='Show specific pair (e.g., -p XLF XLI)')
    parser.add_argument('--index', '-i', type=int, default=None,
                        help='Show trade at specific index')
    parser.add_argument('--all', '-a', action='store_true',
                        help='Generate visualizations for ALL trades')
    
    parser.add_argument('--config', '-c', type=str, default=None,
                        help='Config file to override data settings')
    
    args = parser.parse_args()
    
    try:
        prices, trades, trades_path = load_data(args.trades, args.config)
        config_thresholds = load_config_thresholds(trades_path)
        
        # Add sector info if missing
        if 'sector' not in trades.columns:
            sectors = load_etf_sectors()
            trades['sector'] = trades['leg_x'].map(sectors).fillna('UNKNOWN')
            
        print(f"Using thresholds: entry=±{config_thresholds['entry_threshold_sigma']}, "
              f"exit=±{config_thresholds['exit_threshold_sigma']}, "
              f"stop=±{config_thresholds['stop_loss_sigma']}")
        
        # Filter trades based on arguments
        trades_to_show = pd.DataFrame()
        
        if args.all:
            trades_to_show = trades
        elif args.best_worst:
            sorted_trades = trades.sort_values('pnl', ascending=False)
            trades_to_show = pd.concat([
                sorted_trades.head(args.best_worst),
                sorted_trades.tail(args.best_worst)
            ])
        elif args.year:
            if 'trading_year' in trades.columns:
                trades_to_show = trades[trades['trading_year'] == args.year]
            else:
                trades_to_show = trades[trades['entry_date'].dt.year == args.year]
        elif args.pair:
            etf1, etf2 = args.pair
            mask = ((trades['leg_x'] == etf1) & (trades['leg_y'] == etf2)) | \
                   ((trades['leg_x'] == etf2) & (trades['leg_y'] == etf1))
            trades_to_show = trades[mask]
        elif args.index is not None:
            if 0 <= args.index < len(trades):
                trades_to_show = trades.iloc[[args.index]]
            else:
                print(f"Index out of range. Total trades: {len(trades)}")
        else:
            list_trades_summary(trades, trades_path)
            print("\nUse arguments to visualize specific trades.")
            
        # Visualize selected trades
        if not trades_to_show.empty:
            print(f"\nVisualizing {len(trades_to_show)} trades...")
            for idx, trade in trades_to_show.iterrows():
                try:
                    etf1, etf2 = trade['leg_x'], trade['leg_y']
                    date_str = trade['entry_date'].strftime('%Y%m%d')
                    result = "WIN" if trade['pnl'] > 0 else "LOSS"
                    filename = f"trade_{result}_{etf1}_{etf2}_{date_str}.png"
                    
                    visualize_trade_enhanced(
                        trade, prices, 
                        save_path=OUTPUT_DIR / filename,
                        config_thresholds=config_thresholds
                    )
                except Exception as e:
                    print(f"Error visualizing trade {idx}: {e}")
                    
    except Exception as e:
        print(f"Error: {e}")
