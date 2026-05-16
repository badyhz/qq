from __future__ import annotations

from typing import Final


VALID_MARKET_TYPES: Final[set[str]] = {"spot", "futures"}

BASE_URLS: Final[dict[str, dict[str, str]]] = {
    "spot": {
        "live": "https://api.binance.com",
        "testnet": "https://testnet.binance.vision",
        "sandbox": "https://testnet.binance.vision",
    },
    "futures": {
        "live": "https://fapi.binance.com",
        "testnet": "https://demo-fapi.binance.com",
        "sandbox": "https://demo-fapi.binance.com",
    },
}

ENDPOINT_PATHS: Final[dict[str, dict[str, str]]] = {
    "spot": {
        "ping": "/api/v3/ping",
        "time": "/api/v3/time",
        "account": "/api/v3/account",
        "exchange_info": "/api/v3/exchangeInfo",
        "order": "/api/v3/order",
        "open_orders": "/api/v3/openOrders",
        "positions": "",
    },
    "futures": {
        "ping": "/fapi/v1/ping",
        "time": "/fapi/v1/time",
        "account": "/fapi/v2/account",
        "exchange_info": "/fapi/v1/exchangeInfo",
        "order": "/fapi/v1/order",
        "open_orders": "/fapi/v1/openOrders",
        "positions": "/fapi/v2/positionRisk",
    },
}


def resolve_binance_market_type(market_type: str) -> str:
    market = str(market_type or "spot").strip().lower()
    return market if market in VALID_MARKET_TYPES else "spot"


def resolve_binance_base_url(environment: str, market_type: str = "spot") -> str:
    env = str(environment or "live").strip().lower()
    market = resolve_binance_market_type(market_type)
    catalog = BASE_URLS.get(market, BASE_URLS["spot"])
    return catalog.get(env, catalog["live"])


def resolve_binance_path(name: str, market_type: str = "spot") -> str:
    key = str(name or "").strip().lower()
    market = resolve_binance_market_type(market_type)
    return ENDPOINT_PATHS.get(market, ENDPOINT_PATHS["spot"]).get(key, "")


def build_binance_url(*, environment: str, path: str, market_type: str = "spot") -> str:
    base_url = resolve_binance_base_url(environment, market_type=market_type)
    normalized_path = str(path or "").strip()
    if not normalized_path.startswith("/"):
        normalized_path = f"/{normalized_path}"
    return f"{base_url}{normalized_path}"


def resolve_account_route(*, environment: str, market_type: str = "spot") -> dict[str, str]:
    resolved_market_type = resolve_binance_market_type(market_type)
    account_path = resolve_binance_path("account", market_type=resolved_market_type)
    base_url = resolve_binance_base_url(environment, market_type=resolved_market_type)
    return {
        "market_type": resolved_market_type,
        "resolved_base_url": base_url,
        "resolved_account_path": account_path,
        "url": build_binance_url(
            environment=environment,
            path=account_path,
            market_type=resolved_market_type,
        ),
    }
