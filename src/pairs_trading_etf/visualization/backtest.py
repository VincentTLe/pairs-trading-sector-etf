"""
Backtest visualization module.

This module provides functions to visualize backtest results, including:
- Individual trade analysis (prices, spreads, z-scores, PnL)
- Portfolio performance dashboards
- Cointegration heatmaps
- Signal analysis

Inspired by standard pairs trading analysis notebooks but adapted for production usage.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from typing import Optional, Dict, Tuple, List, Union

# Try to import seaborn for better styling
try:
    import seaborn as sns
    sns.set(style="whitegrid")
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False
    # Set matplotlib style similar to seaborn whitegrid
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    plt.rcParams['grid.linestyle'] = ':'
    plt.rcParams['grid.linewidth'] = 0.5
    plt.rcParams['grid.alpha'] = 0.5


def plot_cointegration_heatmap(formation_stats: dict, save_path: Optional[Path] = None) -> plt.Figure:
    """
    Plot heatmap of cointegration p-values.

    Parameters
    ----------
    formation_stats : dict
        Dict with pair tuples as keys and stats dicts as values.
    save_path : Path, optional
        Path to save the figure.

    Returns
    -------
    plt.Figure
        The generated figure.
    """
    # Extract p-values
    pairs = list(formation_stats.keys())
    if len(pairs) == 0:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No pairs to visualize", ha='center', va='center')
        return fig

    # Get unique ETFs
    all_etfs = sorted(set([etf for pair in pairs for etf in pair]))
    n = len(all_etfs)

    # Create p-value matrix
    pvalue_matrix = np.ones((n, n))  # Default 1.0 (no cointegration)

    for pair, stats in formation_stats.items():
        etf1, etf2 = pair
        if etf1 in all_etfs and etf2 in all_etfs:
            i = all_etfs.index(etf1)
            j = all_etfs.index(etf2)
            pval = stats.get('pvalue', 1.0)
            pvalue_matrix[i, j] = pval
            pvalue_matrix[j, i] = pval  # Symmetric

    # Plot
    fig, ax = plt.subplots(figsize=(14, 12))

    # Mask diagonal and upper triangle
    mask = np.triu(np.ones_like(pvalue_matrix, dtype=bool))

    # Heatmap - only show significant pairs (p < 0.05)
    if HAS_SEABORN:
        sns.heatmap(pvalue_matrix,
                    xticklabels=all_etfs,
                    yticklabels=all_etfs,
                    cmap='RdYlGn_r',
                    mask=mask | (pvalue_matrix >= 0.05),
                    annot=True,
                    fmt='.3f',
                    cbar_kws={'label': 'Cointegration p-value'},
                    vmin=0,
                    vmax=0.05,
                    ax=ax)
    else:
        # Fallback to matplotlib imshow
        masked_data = np.ma.array(pvalue_matrix, mask=mask | (pvalue_matrix >= 0.05))
        im = ax.imshow(masked_data, cmap='RdYlGn_r', vmin=0, vmax=0.05, aspect='auto')
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(all_etfs, rotation=45, ha='right')
        ax.set_yticklabels(all_etfs)
        plt.colorbar(im, ax=ax, label='Cointegration p-value')

    ax.set_title('Cointegration P-Values (Showing p < 0.05)',
                 fontsize=14, fontweight='bold', pad=20)

    plt.tight_layout()

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved cointegration heatmap: {save_path}")

    return fig


def plot_spread_mean_reversion(
    prices: pd.DataFrame,
    pair: Tuple[str, str],
    hedge_ratio: float,
    entry_date: pd.Timestamp,
    exit_date: pd.Timestamp,
    pnl: float,
    save_path: Optional[Path] = None
) -> Optional[plt.Figure]:
    """
    Plot spread with mean line showing mean reversion.

    Parameters
    ----------
    prices : pd.DataFrame
        Price data.
    pair : tuple
        (etf1, etf2).
    hedge_ratio : float
        Hedge ratio used.
    entry_date, exit_date : pd.Timestamp
        Trade entry and exit dates.
    pnl : float
        Trade PnL.
    save_path : Path, optional
        Path to save figure.
    """
    etf1, etf2 = pair

    # Get prices around trade
    start_date = entry_date - pd.Timedelta(days=60)
    end_date = exit_date + pd.Timedelta(days=30)

    mask = (prices.index >= start_date) & (prices.index <= end_date)
    p1 = prices.loc[mask, etf1].dropna()
    p2 = prices.loc[mask, etf2].dropna()

    # Align
    common_idx = p1.index.intersection(p2.index)
    p1 = p1.loc[common_idx]
    p2 = p2.loc[common_idx]

    if len(p1) < 10:
        return None

    # Calculate spread (log space)
    spread = np.log(p1) - hedge_ratio * np.log(p2)

    # Plot
    fig, ax = plt.subplots(figsize=(12, 6))

    # Spread line
    ax.plot(spread.index, spread.values, linewidth=1.5, color='#2c3e50', label='Spread')

    # Mean line
    ax.axhline(spread.mean(), color='red', linestyle='--', linewidth=1.5, label='Mean')

    # Entry/Exit markers
    ax.axvline(entry_date, color='blue', linestyle=':', alpha=0.7, linewidth=1.5, label='Entry')
    ax.axvline(exit_date, color='purple', linestyle=':', alpha=0.7, linewidth=1.5, label='Exit')

    # Shade trade period
    ax.axvspan(entry_date, exit_date, alpha=0.15,
               color='green' if pnl > 0 else 'red')

    # Labels
    result_str = "WIN" if pnl > 0 else "LOSS"
    ax.set_title(f'[{result_str}] Spread Mean Reversion: {etf1} / {etf2} | PnL: ${pnl:+,.0f}',
                 fontsize=12, fontweight='bold')
    ax.set_xlabel('Date', fontsize=10)
    ax.set_ylabel('Log Spread', fontsize=10)
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3)

    # Date formatting
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved spread plot: {save_path}")

    return fig


def plot_zscore_with_signals(
    prices: pd.DataFrame,
    pair: Tuple[str, str],
    hedge_ratio: float,
    half_life: float,
    entry_date: pd.Timestamp,
    exit_date: pd.Timestamp,
    entry_thresh: float = 2.0,
    exit_thresh: float = 0.5,
    stop_loss_thresh: float = 4.0,
    save_path: Optional[Path] = None
) -> Optional[plt.Figure]:
    """
    Z-score with trading signals (buy/sell triangles).

    Parameters
    ----------
    prices : pd.DataFrame
        Price data.
    pair : tuple
        (etf1, etf2).
    hedge_ratio : float
        Hedge ratio.
    half_life : float
        Half-life for lookback calculation.
    entry_date, exit_date : pd.Timestamp
        Trade dates.
    entry_thresh, exit_thresh, stop_loss_thresh : float
        Thresholds for z-score.
    save_path : Path, optional
        Path to save figure.
    """
    etf1, etf2 = pair

    # Get extended window
    start_date = entry_date - pd.Timedelta(days=90)
    end_date = exit_date + pd.Timedelta(days=30)

    mask = (prices.index >= start_date) & (prices.index <= end_date)
    p1 = prices.loc[mask, etf1].dropna()
    p2 = prices.loc[mask, etf2].dropna()

    common_idx = p1.index.intersection(p2.index)
    p1 = p1.loc[common_idx]
    p2 = p2.loc[common_idx]

    if len(p1) < 20:
        return None

    # Spread
    spread = np.log(p1) - hedge_ratio * np.log(p2)

    # Z-score with adaptive lookback (matching engine logic roughly)
    lookback = int(max(30, min(120, 4 * half_life))) if not np.isnan(half_life) else 60
    lookback = min(lookback, len(spread))

    spread_mean = spread.rolling(window=lookback, min_periods=10).mean()
    spread_std = spread.rolling(window=lookback, min_periods=10).std()
    zscore = (spread - spread_mean) / spread_std

    # Plot
    fig, ax = plt.subplots(figsize=(12, 6))

    # Z-score line
    ax.plot(zscore.index, zscore.values, linewidth=1.5, color='#34495e', label='Z-Score')

    # Threshold bands
    ax.axhline(0, color='black', linestyle='-', alpha=0.5)
    ax.axhline(entry_thresh, color='red', linestyle='--', alpha=0.7, label=f'Entry (±{entry_thresh})')
    ax.axhline(-entry_thresh, color='red', linestyle='--', alpha=0.7)
    ax.axhline(exit_thresh, color='green', linestyle=':', alpha=0.7, label=f'Exit (±{exit_thresh})')
    ax.axhline(-exit_thresh, color='green', linestyle=':', alpha=0.7)
    ax.axhline(stop_loss_thresh, color='darkred', linestyle='-.', alpha=0.5, label=f'Stop (±{stop_loss_thresh})')
    ax.axhline(-stop_loss_thresh, color='darkred', linestyle='-.', alpha=0.5)

    # Find entry/exit points
    if entry_date in common_idx and exit_date in common_idx:
        entry_idx = common_idx.get_indexer([entry_date], method='nearest')[0]
        exit_idx = common_idx.get_indexer([exit_date], method='nearest')[0]

        # Entry marker
        entry_z = zscore.iloc[entry_idx]
        ax.scatter([common_idx[entry_idx]], [entry_z], marker='^', s=150,
                   color='green', edgecolor='black', linewidth=1.5, zorder=5,
                   label='Entry Signal')

        # Exit marker
        exit_z = zscore.iloc[exit_idx]
        ax.scatter([common_idx[exit_idx]], [exit_z], marker='v', s=150,
                   color='red', edgecolor='black', linewidth=1.5, zorder=5,
                   label='Exit Signal')

    ax.set_title(f'Trading Signals: {etf1} / {etf2} (HL={half_life:.1f}d)',
                 fontsize=12, fontweight='bold')
    ax.set_xlabel('Date', fontsize=10)
    ax.set_ylabel('Z-Score', fontsize=10)
    ax.set_ylim(-max(5, stop_loss_thresh + 1), max(5, stop_loss_thresh + 1))
    ax.legend(loc='upper right', fontsize=8, ncol=3)
    ax.grid(True, alpha=0.3)

    # Date formatting
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved z-score signals: {save_path}")

    return fig


def plot_performance_dashboard(trades_df: pd.DataFrame, config_name: str = "default", save_path: Optional[Path] = None) -> plt.Figure:
    """
    Create summary dashboard with key performance metrics.

    Parameters
    ----------
    trades_df : pd.DataFrame
        DataFrame of trades.
    config_name : str
        Name of the configuration/experiment.
    save_path : Path, optional
        Path to save figure.
    """
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

    # Title
    fig.suptitle(f'Backtest Performance Dashboard\nConfig: {config_name}',
                 fontsize=16, fontweight='bold', y=0.98)

    # 1. Cumulative PnL
    ax1 = fig.add_subplot(gs[0, :])
    if 'exit_date' in trades_df.columns and not trades_df.empty:
        trades_sorted = trades_df.sort_values('exit_date')
        cum_pnl = trades_sorted['pnl'].cumsum()
        ax1.fill_between(range(len(cum_pnl)), 0, cum_pnl.values,
                         where=cum_pnl.values >= 0, color='green', alpha=0.3)
        ax1.fill_between(range(len(cum_pnl)), 0, cum_pnl.values,
                         where=cum_pnl.values < 0, color='red', alpha=0.3)
        ax1.plot(cum_pnl.values, linewidth=2.5, color='black')
        ax1.set_title('Cumulative PnL', fontsize=12, fontweight='bold')
        ax1.set_xlabel('Trade Number')
        ax1.set_ylabel('Cumulative PnL ($)')
        ax1.axhline(0, color='gray', linestyle='--', alpha=0.5)
        ax1.grid(True, alpha=0.3)

    # 2. PnL Distribution
    ax2 = fig.add_subplot(gs[1, 0])
    if not trades_df.empty:
        ax2.hist(trades_df['pnl'], bins=30, edgecolor='black', alpha=0.7, color='steelblue')
        ax2.axvline(0, color='red', linestyle='--', linewidth=2)
        ax2.axvline(trades_df['pnl'].mean(), color='green', linestyle='--', linewidth=2,
                    label=f'Mean: ${trades_df["pnl"].mean():.2f}')
        ax2.set_title('PnL Distribution', fontsize=11, fontweight='bold')
        ax2.set_xlabel('PnL ($)')
        ax2.set_ylabel('Frequency')
        ax2.legend(fontsize=9)
        ax2.grid(True, alpha=0.3)

    # 3. Win Rate by Exit Reason
    ax3 = fig.add_subplot(gs[1, 1])
    if 'exit_reason' in trades_df.columns and not trades_df.empty:
        exit_counts = trades_df.groupby('exit_reason').size()
        colors = ['#27ae60', '#e74c3c', '#3498db', '#f39c12', '#9b59b6']
        # Handle case where there are more exit reasons than colors
        bar_colors = (colors * (len(exit_counts) // len(colors) + 1))[:len(exit_counts)]
        exit_counts.plot(kind='bar', ax=ax3, color=bar_colors,
                        edgecolor='black', alpha=0.8)
        ax3.set_title('Trades by Exit Reason', fontsize=11, fontweight='bold')
        ax3.set_xlabel('Exit Reason')
        ax3.set_ylabel('Count')
        ax3.tick_params(axis='x', rotation=45)
        ax3.grid(True, alpha=0.3, axis='y')

    # 4. Holding Days Distribution
    ax4 = fig.add_subplot(gs[1, 2])
    if 'holding_days' in trades_df.columns and not trades_df.empty:
        ax4.hist(trades_df['holding_days'], bins=20, edgecolor='black',
                alpha=0.7, color='coral')
        ax4.axvline(trades_df['holding_days'].mean(), color='blue',
                   linestyle='--', linewidth=2,
                   label=f'Mean: {trades_df["holding_days"].mean():.1f}d')
        ax4.set_title('Holding Period Distribution', fontsize=11, fontweight='bold')
        ax4.set_xlabel('Days')
        ax4.set_ylabel('Frequency')
        ax4.legend(fontsize=9)
        ax4.grid(True, alpha=0.3)

    # 5. Performance Metrics Table
    ax5 = fig.add_subplot(gs[2, :])
    ax5.axis('off')

    # Calculate metrics
    total_trades = len(trades_df)
    winners = len(trades_df[trades_df['pnl'] > 0])
    losers = len(trades_df[trades_df['pnl'] < 0])
    win_rate = (winners / total_trades * 100) if total_trades > 0 else 0
    total_pnl = trades_df['pnl'].sum() if not trades_df.empty else 0
    avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winners > 0 else 0
    avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean() if losers > 0 else 0
    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    avg_holding = trades_df['holding_days'].mean() if 'holding_days' in trades_df.columns else 0

    metrics_text = f"""
    PERFORMANCE METRICS

    Total Trades: {total_trades}
    Winners: {winners} ({win_rate:.1f}%)
    Losers: {losers} ({100-win_rate:.1f}%)

    Total PnL: ${total_pnl:+,.2f}
    Avg Win: ${avg_win:,.2f}
    Avg Loss: ${avg_loss:,.2f}
    Profit Factor: {profit_factor:.2f}

    Avg Holding Period: {avg_holding:.1f} days
    """

    ax5.text(0.5, 0.5, metrics_text, transform=ax5.transAxes,
             fontsize=11, verticalalignment='center', horizontalalignment='center',
             family='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()

    # Save
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"\nSaved dashboard: {save_path}")

    return fig


def visualize_trade_enhanced(
    trade_row: pd.Series,
    prices: pd.DataFrame,
    capital_at_entry: float = 50000,
    context_days: int = 30,
    save_path: Optional[Path] = None,
    config_thresholds: Optional[Dict] = None
) -> Optional[plt.Figure]:
    """
    Enhanced comprehensive visualization for a single trade.
    Plots prices, PnL, and Z-score in a single figure.

    Parameters
    ----------
    trade_row : pd.Series
        Row from trades DataFrame containing trade details.
    prices : pd.DataFrame
        Price data.
    capital_at_entry : float
        Capital at time of trade.
    context_days : int
        Days before/after trade to visualize.
    save_path : Path, optional
        Path to save figure.
    config_thresholds : dict, optional
        Dictionary with 'entry_threshold_sigma', 'exit_threshold_sigma', 'stop_loss_sigma'.
    """
    if config_thresholds is None:
        config_thresholds = {
            'entry_threshold_sigma': 2.0,
            'exit_threshold_sigma': 0.5,
            'stop_loss_sigma': 4.0,
            'zscore_lookback': 60
        }

    # Extract trade info
    etf1 = trade_row['leg_x']
    etf2 = trade_row['leg_y']
    entry_date = pd.to_datetime(trade_row['entry_date'])
    exit_date = pd.to_datetime(trade_row['exit_date'])
    direction = trade_row['direction']
    pnl = trade_row['pnl']
    hedge_ratio = trade_row['hedge_ratio']
    exit_reason = trade_row.get('exit_reason', 'unknown')
    entry_z = trade_row.get('entry_z', np.nan)
    exit_z = trade_row.get('exit_z', np.nan)

    # Get additional stats if available
    half_life = trade_row.get('half_life', np.nan)
    pvalue = trade_row.get('pvalue', np.nan)
    sector = trade_row.get('sector', 'UNKNOWN')
    trading_year = trade_row.get('trading_year', entry_date.year)

    # Position sizes
    qty_x = trade_row.get('qty_x', np.nan)
    qty_y = trade_row.get('qty_y', np.nan)
    entry_px = trade_row.get('entry_px', np.nan)
    entry_py = trade_row.get('entry_py', np.nan)

    if not np.isnan(qty_x) and not np.isnan(entry_px):
        position_capital = abs(qty_x) * entry_px + abs(qty_y) * entry_py
    else:
        position_capital = trade_row.get('position_capital', 15000)

    # Determine direction
    is_long_spread = (direction == "LONG" or direction == 1)

    # Get data
    start_date = entry_date - pd.Timedelta(days=context_days)
    end_date = exit_date + pd.Timedelta(days=context_days)

    mask = (prices.index >= start_date) & (prices.index <= end_date)
    p1 = prices.loc[mask, etf1].dropna()
    p2 = prices.loc[mask, etf2].dropna()

    common_idx = p1.index.intersection(p2.index)
    p1 = p1.loc[common_idx]
    p2 = p2.loc[common_idx]

    if len(p1) < 5:
        return None

    # Entry/Exit indices
    entry_idx = common_idx.get_indexer([entry_date], method='nearest')[0]
    exit_idx = common_idx.get_indexer([exit_date], method='nearest')[0]

    entry_p1 = p1.iloc[entry_idx]
    entry_p2 = p2.iloc[entry_idx]
    pct_change1 = (p1 / entry_p1 - 1) * 100
    pct_change2 = (p2 / entry_p2 - 1) * 100

    # Spread & Z-Score
    log_spread = np.log(p1) - hedge_ratio * np.log(p2)

    lookback = config_thresholds.get('zscore_lookback', 60)
    if not np.isnan(half_life):
        lookback = int(max(30, min(120, 4 * half_life)))
        lookback = min(lookback, len(log_spread))
    else:
        lookback = min(lookback, len(log_spread) // 2)

    spread_mean = log_spread.rolling(window=lookback, min_periods=10).mean()
    spread_std = log_spread.rolling(window=lookback, min_periods=10).std()
    zscore = (log_spread - spread_mean) / spread_std

    # Estimate PnL series
    # Logic simplified: assume PnL varies with price diff relative to entry
    # This is an approximation for visualization
    if is_long_spread:
        # Long spread = Long A, Short B
        # pnl approx proportional to (p1/p1_entry - p2/p2_entry) ? No, depends on amounts
        # Let's use qtys if available
        if not np.isnan(qty_x):
            pnl_x = qty_x * (p1 - entry_p1)
            pnl_y = qty_y * (p2 - entry_p2)
        else:
            # Fallback estimation
            notional_x = position_capital / (1 + abs(hedge_ratio))
            notional_y = abs(hedge_ratio) * notional_x
            qty_x_est = notional_x / entry_p1
            qty_y_est = -notional_y / entry_p2
            pnl_x = qty_x_est * (p1 - entry_p1)
            pnl_y = qty_y_est * (p2 - entry_p2)
    else:
        # Short spread = Short A, Long B
        if not np.isnan(qty_x):
            pnl_x = qty_x * (p1 - entry_p1)
            pnl_y = qty_y * (p2 - entry_p2)
        else:
            notional_x = position_capital / (1 + abs(hedge_ratio))
            notional_y = abs(hedge_ratio) * notional_x
            qty_x_est = -notional_x / entry_p1
            qty_y_est = notional_y / entry_p2
            pnl_x = qty_x_est * (p1 - entry_p1)
            pnl_y = qty_y_est * (p2 - entry_p2)

    total_pnl = pnl_x + pnl_y

    # PLOTTING
    fig = plt.figure(figsize=(16, 20))
    gs = fig.add_gridspec(4, 2, height_ratios=[0.28, 1, 1, 0.9],
                          hspace=0.3, wspace=0.25,
                          left=0.06, right=0.94, top=0.96, bottom=0.04)

    # 0. HEADER
    ax_header = fig.add_subplot(gs[0, :])
    ax_header.axis('off')

    result_text = "WIN" if pnl > 0 else "LOSS"
    result_color = '#27ae60' if pnl > 0 else '#e74c3c'
    holding_days = (exit_date - entry_date).days
    pnl_pct = (pnl / position_capital) * 100 if position_capital > 0 else 0
    hl_ratio = holding_days / half_life if half_life > 0 else 0

    title_str = (f"[{result_text}] {etf1} / {etf2}  |  "
                 f"{entry_date.strftime('%Y-%m-%d')} → {exit_date.strftime('%Y-%m-%d')} ({holding_days}d)  |  "
                 f"PnL: ${pnl:+,.0f} ({pnl_pct:+.1f}%)")
    ax_header.text(0.5, 0.88, title_str, transform=ax_header.transAxes,
                   fontsize=14, fontweight='bold', color=result_color, ha='center')

    info_line1 = (f"Sector: {sector}  |  "
                  f"{'LONG' if is_long_spread else 'SHORT'} spread "
                  f"({etf1} {'L' if is_long_spread else 'S'} / {etf2} {'S' if is_long_spread else 'L'})  |  "
                  f"Exit: {exit_reason}")
    ax_header.text(0.5, 0.62, info_line1, transform=ax_header.transAxes,
                   fontsize=10, ha='center')

    pvalue_str = f"{pvalue:.3f}" if not np.isnan(pvalue) else "N/A"
    info_line2 = (
        f"Portfolio: ${capital_at_entry:,.0f}  |  Position: ${position_capital:,.0f}  |  "
        f"Hedge Ratio: {hedge_ratio:.3f}  |  P-value: {pvalue_str}  |  Year: {trading_year}"
    )
    ax_header.text(0.5, 0.38, info_line2, transform=ax_header.transAxes,
                   fontsize=9, ha='center', color='#444444')

    stats_line = (f"Entry Z: {entry_z:.2f} → Exit Z: {exit_z:.2f}  |  "
                  f"Half-life: {half_life:.1f}d  |  Holding: {holding_days}d ({hl_ratio:.1f}x HL)")
    ax_header.text(0.5, 0.14, stats_line, transform=ax_header.transAxes,
                   fontsize=9, ha='center', color='#555555')

    # 1. PRICES 1
    ax1 = fig.add_subplot(gs[1, 0])
    ax1.plot(p1.index, p1.values, color='#3498db', linewidth=2, label=f'{etf1}')
    ax1.axvline(entry_date, color='blue', linestyle='--', alpha=0.5)
    ax1.axvline(exit_date, color='purple', linestyle='--', alpha=0.5)
    ax1.axvspan(entry_date, exit_date, alpha=0.1, color='blue')
    ax1.scatter([common_idx[entry_idx]], [entry_p1], marker='^', s=100, color='blue', zorder=5)
    ax1.scatter([common_idx[exit_idx]], [p1.iloc[exit_idx]], marker='v', s=100, color='purple', zorder=5)
    ax1.set_title(f'{etf1} Price', fontsize=11, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3)

    # 2. PRICES 2
    ax2 = fig.add_subplot(gs[1, 1])
    ax2.plot(p2.index, p2.values, color='#e74c3c', linewidth=2, label=f'{etf2}')
    ax2.axvline(entry_date, color='blue', linestyle='--', alpha=0.5)
    ax2.axvline(exit_date, color='purple', linestyle='--', alpha=0.5)
    ax2.axvspan(entry_date, exit_date, alpha=0.1, color='blue')
    ax2.scatter([common_idx[entry_idx]], [entry_p2], marker='^', s=100, color='blue', zorder=5)
    ax2.scatter([common_idx[exit_idx]], [p2.iloc[exit_idx]], marker='v', s=100, color='purple', zorder=5)
    ax2.set_title(f'{etf2} Price', fontsize=11, fontweight='bold')
    ax2.legend(loc='upper left', fontsize=8)
    ax2.grid(True, alpha=0.3)

    # 3. % CHANGE
    ax3 = fig.add_subplot(gs[2, 0])
    ax3.plot(pct_change1.index, pct_change1.values, label=f'{etf1} %', color='#27ae60')
    ax3.plot(pct_change2.index, pct_change2.values, label=f'{etf2} %', color='#e74c3c')
    ax3.axvspan(entry_date, exit_date, alpha=0.1, color='gray')
    ax3.set_title('% Change from Entry', fontsize=11, fontweight='bold')
    ax3.legend(loc='best', fontsize=8)
    ax3.grid(True, alpha=0.3)

    # 4. Z-SCORE
    ax4 = fig.add_subplot(gs[2, 1])
    ax4.plot(zscore.index, zscore.values, color='#2c3e50', linewidth=1.5, label='Z-Score')
    e_thresh = config_thresholds.get('entry_threshold_sigma', 2.0)
    x_thresh = config_thresholds.get('exit_threshold_sigma', 0.5)
    s_thresh = config_thresholds.get('stop_loss_sigma', 4.0)

    ax4.axhline(e_thresh, color='red', linestyle='--', alpha=0.5)
    ax4.axhline(-e_thresh, color='red', linestyle='--', alpha=0.5)
    ax4.axhline(x_thresh, color='green', linestyle=':', alpha=0.5)
    ax4.axhline(-x_thresh, color='green', linestyle=':', alpha=0.5)
    ax4.axhline(s_thresh, color='darkred', linestyle='-.', alpha=0.5)
    ax4.axhline(-s_thresh, color='darkred', linestyle='-.', alpha=0.5)
    
    # Mark entry/exit z
    calc_entry_z = zscore.iloc[entry_idx]
    calc_exit_z = zscore.iloc[exit_idx]
    ax4.scatter([common_idx[entry_idx]], [calc_entry_z], marker='^', s=100, color='blue', zorder=5)
    ax4.scatter([common_idx[exit_idx]], [calc_exit_z], marker='v', s=100, color='purple', zorder=5)

    ax4.set_title('Spread Z-Score', fontsize=11, fontweight='bold')
    ax4.grid(True, alpha=0.3)

    # 5. PNL EVOLUTION
    ax5 = fig.add_subplot(gs[3, :])
    trade_mask = common_idx >= entry_date
    pnl_during = total_pnl[trade_mask]
    
    ax5.plot(pnl_during.index, pnl_during.values, color='black', linewidth=2, label='Total PnL')
    ax5.fill_between(pnl_during.index, 0, pnl_during.values, 
                     where=pnl_during.values >= 0, color='green', alpha=0.3)
    ax5.fill_between(pnl_during.index, 0, pnl_during.values, 
                     where=pnl_during.values < 0, color='red', alpha=0.3)
    ax5.axhline(0, color='gray', linestyle='-', alpha=0.5)
    ax5.set_title('PnL Evolution', fontsize=11, fontweight='bold')
    ax5.set_ylabel('PnL ($)')
    ax5.grid(True, alpha=0.3)

    # Format dates
    for ax in [ax1, ax2, ax3, ax4, ax5]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=100, bbox_inches='tight', facecolor='white')
        print(f"Saved trade visual: {save_path}")

    return fig
