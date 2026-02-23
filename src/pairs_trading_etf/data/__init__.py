"""Data ingestion, validation, and global ETF data utilities."""

from pairs_trading_etf.data.loader import (
    PriceFrame,
    PriceLoaderError,
    build_price_frame,
    load_price_history,
)
from pairs_trading_etf.data.ingestion import (
    download_etf_data,
    save_raw_data,
    validate_price_data,
)
from pairs_trading_etf.data.universe import (
    ETFMetadata,
    ETFUniverse,
    load_configured_universe,
    load_etf_metadata,
)

__all__ = [
    # Loader
    "PriceFrame",
    "PriceLoaderError",
    "build_price_frame",
    "load_price_history",
    # Ingestion
    "download_etf_data",
    "save_raw_data",
    "validate_price_data",
    # Universe
    "ETFMetadata",
    "ETFUniverse",
    "load_configured_universe",
    "load_etf_metadata",
]
