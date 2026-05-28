"""Sample live fixture for frozen inventory tests.

This file is NEVER imported or executed by the scanner.
It exists only to test risk keyword detection and category classification.
"""

import requests  # noqa: F401
from binance.client import Client  # noqa: F401

LIVE_TRADING_ENABLED = True
API_KEY = "DO_NOT_PUT_REAL_KEYS_HERE"
API_SECRET = "DO_NOT_PUT_REAL_KEYS_HERE"

def place_live_order(symbol: str, side: str, qty: float):
    """Simulates a live order placement. FAPI endpoint."""
    pass
