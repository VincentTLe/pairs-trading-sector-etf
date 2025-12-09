"""
Position management for pairs trading.

This module handles:
- Position state tracking
- Trade entry/exit execution
- PnL calculation
- Pair blacklist management
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..constants import BLACKLIST_STOP_LOSS_RATE, BLACKLIST_MIN_TRADES
from ..utils.sectors import get_sector

logger = logging.getLogger(__name__)


# =============================================================================
# POSITION DATA STRUCTURES
# =============================================================================

@dataclass
class PositionEntry:
    """Data for an open position."""
    t: int                          # Time index at entry
    date: pd.Timestamp              # Entry date
    signal_date: pd.Timestamp       # Signal date (t-1 for look-ahead bias fix)
    z: float                        # Z-score at signal time
    spread: float                   # Spread value at signal time
    px: float                       # Execution price for leg X
    py: float                       # Execution price for leg Y
    hr: float                       # Hedge ratio at entry
    qty_x: float                    # Quantity of leg X
    qty_y: float                    # Quantity of leg Y
    capital: float                  # Capital at entry
    mu_entry: float                 # Mean at entry (for fixed exit params)
    sigma_entry: float              # Std at entry (for fixed exit params)


@dataclass
class TradeRecord:
    """Completed trade record."""
    pair: Tuple[str, str]
    leg_x: str
    leg_y: str
    sector: str
    direction: str                  # 'LONG' or 'SHORT'
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    holding_days: int
    entry_z: float
    exit_z: float
    hedge_ratio: float
    half_life: float
    pnl: float
    exit_reason: str
    capital_at_entry: float
    qty_x: float
    qty_y: float
    entry_px: float
    entry_py: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility."""
        return {
            'pair': self.pair,
            'leg_x': self.leg_x,
            'leg_y': self.leg_y,
            'sector': self.sector,
            'direction': self.direction,
            'entry_date': self.entry_date,
            'exit_date': self.exit_date,
            'holding_days': self.holding_days,
            'entry_z': self.entry_z,
            'exit_z': self.exit_z,
            'hedge_ratio': self.hedge_ratio,
            'half_life': self.half_life,
            'pnl': self.pnl,
            'exit_reason': self.exit_reason,
            'capital_at_entry': self.capital_at_entry,
            'qty_x': self.qty_x,
            'qty_y': self.qty_y,
            'entry_px': self.entry_px,
            'entry_py': self.entry_py,
        }


# =============================================================================
# BLACKLIST MANAGEMENT
# =============================================================================

class PairBlacklist:
    """Manages pairs that should be excluded due to poor performance."""

    def __init__(
        self,
        threshold: float = BLACKLIST_STOP_LOSS_RATE,
        min_trades: int = BLACKLIST_MIN_TRADES
    ):
        """
        Initialize blacklist manager.

        Parameters
        ----------
        threshold : float
            Stop-loss rate above which to blacklist pair
        min_trades : int
            Minimum trades before evaluating for blacklist
        """
        self.threshold = threshold
        self.min_trades = min_trades
        self.blacklist: set = set()
        self.pair_stats: Dict[Tuple[str, str], Dict[str, int]] = defaultdict(
            lambda: {'trades': 0, 'stop_losses': 0}
        )

    def update(self, trades: List[Dict]) -> None:
        """
        Update blacklist based on new trades.

        Parameters
        ----------
        trades : list
            List of trade dictionaries
        """
        for trade in trades:
            pair = trade['pair']
            self.pair_stats[pair]['trades'] += 1
            if trade['exit_reason'] in ('stop_loss', 'stop_loss_time'):
                self.pair_stats[pair]['stop_losses'] += 1

        for pair, stats in self.pair_stats.items():
            if stats['trades'] >= self.min_trades:
                sl_rate = stats['stop_losses'] / stats['trades']
                if sl_rate > self.threshold and pair not in self.blacklist:
                    logger.info(f"Blacklisting {pair}: {sl_rate:.1%} stop-loss rate")
                    self.blacklist.add(pair)

    def is_blacklisted(self, pair: Tuple[str, str]) -> bool:
        """Check if pair is blacklisted."""
        return pair in self.blacklist or (pair[1], pair[0]) in self.blacklist

    def get_stats(self, pair: Tuple[str, str]) -> Dict[str, Any]:
        """Get statistics for a pair."""
        stats = self.pair_stats.get(pair, {'trades': 0, 'stop_losses': 0})
        if stats['trades'] > 0:
            stats['stop_loss_rate'] = stats['stop_losses'] / stats['trades']
        else:
            stats['stop_loss_rate'] = 0.0
        return stats


# =============================================================================
# POSITION STATE MANAGEMENT
# =============================================================================

@dataclass
class PositionManager:
    """Manages position state for multiple pairs."""

    pairs: List[Tuple[str, str]]
    position_state: Dict[Tuple[str, str], int] = field(default_factory=dict)
    entry_data: Dict[Tuple[str, str], Dict] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize position state for all pairs."""
        for pair in self.pairs:
            if pair not in self.position_state:
                self.position_state[pair] = 0
            if pair not in self.entry_data:
                self.entry_data[pair] = {}

    def is_flat(self, pair: Tuple[str, str]) -> bool:
        """Check if position is flat (no position)."""
        return self.position_state.get(pair, 0) == 0

    def is_long(self, pair: Tuple[str, str]) -> bool:
        """Check if position is long spread."""
        return self.position_state.get(pair, 0) == 1

    def is_short(self, pair: Tuple[str, str]) -> bool:
        """Check if position is short spread."""
        return self.position_state.get(pair, 0) == -1

    def get_direction(self, pair: Tuple[str, str]) -> int:
        """Get position direction (-1, 0, or 1)."""
        return self.position_state.get(pair, 0)

    def get_entry(self, pair: Tuple[str, str]) -> Dict:
        """Get entry data for a pair."""
        return self.entry_data.get(pair, {})

    def count_active(self) -> int:
        """Count number of active positions."""
        return sum(1 for p in self.pairs if self.position_state.get(p, 0) != 0)

    def enter_long(self, pair: Tuple[str, str], entry: Dict) -> None:
        """Enter long spread position."""
        self.position_state[pair] = 1
        self.entry_data[pair] = entry

    def enter_short(self, pair: Tuple[str, str], entry: Dict) -> None:
        """Enter short spread position."""
        self.position_state[pair] = -1
        self.entry_data[pair] = entry

    def exit_position(self, pair: Tuple[str, str]) -> Dict:
        """Exit position and return entry data."""
        entry = self.entry_data.get(pair, {})
        self.position_state[pair] = 0
        self.entry_data[pair] = {}
        return entry

    def get_open_pairs(self) -> List[Tuple[str, str]]:
        """Get list of pairs with open positions."""
        return [p for p in self.pairs if self.position_state.get(p, 0) != 0]


# =============================================================================
# PNL CALCULATION
# =============================================================================

def calculate_trade_pnl(
    entry: Dict,
    exit_px: float,
    exit_py: float,
    transaction_cost_bps: float = 10.0,
) -> Tuple[float, float]:
    """
    Calculate PnL for a trade.

    Parameters
    ----------
    entry : dict
        Entry data with qty_x, qty_y, px, py
    exit_px : float
        Exit price for leg X
    exit_py : float
        Exit price for leg Y
    transaction_cost_bps : float
        Transaction cost in basis points

    Returns
    -------
    tuple
        (gross_pnl, net_pnl)
    """
    # Calculate gross PnL
    pnl_x = entry['qty_x'] * (exit_px - entry['px'])
    pnl_y = entry['qty_y'] * (exit_py - entry['py'])
    gross_pnl = pnl_x + pnl_y

    # Calculate transaction costs
    entry_notional = abs(entry['qty_x']) * entry['px'] + abs(entry['qty_y']) * entry['py']
    exit_notional = abs(entry['qty_x']) * exit_px + abs(entry['qty_y']) * exit_py
    cost = (entry_notional + exit_notional) * (transaction_cost_bps / 10000)

    net_pnl = gross_pnl - cost

    return gross_pnl, net_pnl


def calculate_position_sizes(
    capital: float,
    hedge_ratio: float,
    px: float,
    py: float,
    direction: int,
) -> Tuple[float, float]:
    """
    Calculate position sizes for a pairs trade.

    Parameters
    ----------
    capital : float
        Capital to allocate to this trade
    hedge_ratio : float
        Hedge ratio (beta)
    px : float
        Price of leg X
    py : float
        Price of leg Y
    direction : int
        1 for long spread, -1 for short spread

    Returns
    -------
    tuple
        (qty_x, qty_y) - signed quantities
    """
    # Allocate capital between legs
    notional_x = capital / (1 + abs(hedge_ratio))
    notional_y = abs(hedge_ratio) * notional_x

    # Calculate quantities
    qty_x = notional_x / px
    qty_y = notional_y / py

    # Apply direction
    if direction == 1:  # Long spread: long X, short Y
        return qty_x, -qty_y
    else:  # Short spread: short X, long Y
        return -qty_x, qty_y


# =============================================================================
# TRADE RECORD CREATION
# =============================================================================

def create_trade_record(
    pair: Tuple[str, str],
    entry: Dict,
    exit_date: pd.Timestamp,
    exit_z: float,
    exit_px: float,
    exit_py: float,
    exit_reason: str,
    half_life: float,
    direction: int,
    current_capital: float,
    transaction_cost_bps: float = 10.0,
) -> Dict[str, Any]:
    """
    Create a trade record dictionary.

    Parameters
    ----------
    pair : tuple
        (leg_x, leg_y) ticker pair
    entry : dict
        Entry data
    exit_date : pd.Timestamp
        Exit date
    exit_z : float
        Z-score at exit
    exit_px : float
        Exit price for leg X
    exit_py : float
        Exit price for leg Y
    exit_reason : str
        Reason for exit
    half_life : float
        Half-life of the pair
    direction : int
        Position direction (1 or -1)
    current_capital : float
        Current portfolio capital
    transaction_cost_bps : float
        Transaction cost in basis points

    Returns
    -------
    dict
        Trade record
    """
    leg_x, leg_y = pair

    # Calculate PnL
    _, net_pnl = calculate_trade_pnl(
        entry, exit_px, exit_py, transaction_cost_bps
    )

    # Calculate holding days
    holding_days = (exit_date - entry['date']).days
    if holding_days < 1:
        # Use index-based calculation if available
        holding_days = max(1, entry.get('holding_days', 1))

    return {
        'pair': pair,
        'leg_x': leg_x,
        'leg_y': leg_y,
        'sector': get_sector(leg_x),
        'direction': 'LONG' if direction == 1 else 'SHORT',
        'entry_date': entry['date'],
        'exit_date': exit_date,
        'holding_days': holding_days,
        'entry_z': entry['z'],
        'exit_z': exit_z,
        'hedge_ratio': entry['hr'],
        'half_life': half_life,
        'pnl': net_pnl,
        'exit_reason': exit_reason,
        'capital_at_entry': entry.get('capital', current_capital),
        'qty_x': entry['qty_x'],
        'qty_y': entry['qty_y'],
        'entry_px': entry['px'],
        'entry_py': entry['py'],
    }


# =============================================================================
# CAPITAL MANAGEMENT
# =============================================================================

def calculate_capital_per_trade(
    current_capital: float,
    max_positions: int,
    n_pairs: int,
    leverage: float = 1.0,
    max_capital_per_trade: float = 0.0,
    compounding: bool = True,
) -> float:
    """
    Calculate capital allocation per trade.

    Parameters
    ----------
    current_capital : float
        Current portfolio capital
    max_positions : int
        Maximum concurrent positions (0 = unlimited)
    n_pairs : int
        Number of available pairs
    leverage : float
        Leverage multiplier
    max_capital_per_trade : float
        Maximum capital per trade (0 = no limit)
    compounding : bool
        Whether to use compounding

    Returns
    -------
    float
        Capital to allocate per trade
    """
    if compounding:
        # Divide available capital among max positions
        max_pos = max_positions if max_positions > 0 else max(5, n_pairs)
        position_capital = (current_capital * leverage) / max(1, max_pos)

        # Apply max capital per trade limit if set
        if max_capital_per_trade > 0:
            position_capital = min(position_capital, max_capital_per_trade)
    else:
        # Fixed capital per trade
        position_capital = current_capital * leverage / max(1, max_positions)

    return position_capital


# =============================================================================
# TRADE SUMMARY STATISTICS
# =============================================================================

def summarize_trades(trades: List[Dict]) -> Dict[str, Any]:
    """
    Calculate summary statistics for a list of trades.

    Parameters
    ----------
    trades : list
        List of trade dictionaries

    Returns
    -------
    dict
        Summary statistics
    """
    if not trades:
        return {
            'n_trades': 0,
            'n_wins': 0,
            'n_losses': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'avg_pnl': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'avg_holding_days': 0.0,
            'exit_reasons': {},
        }

    n_trades = len(trades)
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]

    n_wins = len(wins)
    n_losses = len(losses)

    total_pnl = sum(t['pnl'] for t in trades)
    avg_pnl = total_pnl / n_trades

    avg_win = sum(t['pnl'] for t in wins) / n_wins if wins else 0.0
    avg_loss = sum(t['pnl'] for t in losses) / n_losses if losses else 0.0

    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    avg_holding = sum(t['holding_days'] for t in trades) / n_trades

    exit_reasons = defaultdict(int)
    for t in trades:
        exit_reasons[t['exit_reason']] += 1

    return {
        'n_trades': n_trades,
        'n_wins': n_wins,
        'n_losses': n_losses,
        'win_rate': n_wins / n_trades * 100,
        'total_pnl': total_pnl,
        'avg_pnl': avg_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'avg_holding_days': avg_holding,
        'exit_reasons': dict(exit_reasons),
    }
