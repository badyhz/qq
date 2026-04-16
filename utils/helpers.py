"""."""
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def format_price(value: float) -> str:
    price = float(value)
    abs_price = abs(price)

    if abs_price >= 1000:
        decimals = 2
    elif abs_price >= 1:
        decimals = 4
    elif abs_price >= 0.01:
        decimals = 5
    else:
        decimals = 6

    return f"{price:.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    return f"{value * 100:.{decimals}f}%"


def format_timestamp(timestamp: Optional[int] = None) -> str:
    if timestamp is None:
        return datetime.now(timezone.utc).isoformat()

    return datetime.fromtimestamp(timestamp / 1000, timezone.utc).isoformat()


def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    if data is None:
        return default
    return data.get(key, default)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def truncate_string(s: str, max_length: int, suffix: str = "...") -> str:
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def calculate_avg(lst: List[float]) -> float:
    if not lst:
        return 0.0
    return sum(lst) / len(lst)


def calculate_std(lst: List[float]) -> float:
    if len(lst) < 2:
        return 0.0

    avg = calculate_avg(lst)
    variance = sum((x - avg) ** 2 for x in lst) / len(lst)
    return variance ** 0.5


def format_currency(value: float, currency: str = "USDT") -> str:
    return f"{value:.4f} {currency}"


def is_valid_symbol(symbol: str) -> bool:
    if not symbol or not isinstance(symbol, str):
        return False

    symbol = symbol.strip().upper()

    if len(symbol) < 4:
        return False

    quote_currencies = ['USDT', 'BUSD', 'USDC', 'BTC', 'ETH']
    has_valid_quote = any(symbol.endswith(q) for q in quote_currencies)

    return has_valid_quote


def parse_symbol(symbol: str) -> Optional[tuple]:
    if not is_valid_symbol(symbol):
        return None

    symbol = symbol.strip().upper()

    quote_currencies = ['USDT', 'BUSD', 'USDC', 'BTC', 'ETH']

    for quote in quote_currencies:
        if symbol.endswith(quote):
            base_asset = symbol[:-len(quote)]
            if base_asset:
                return (base_asset, quote)

    return None


def get_current_current_timestamp() -> int:
    return int(time.time() * 1000)
