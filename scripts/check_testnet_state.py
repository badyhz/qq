from __future__ import annotations

import argparse
import json
import os
from typing import Any

from core.binance_testnet_client import BinanceFuturesTestnetClient
from scripts.check_testnet_state_common import (
    build_testnet_state_result,
    normalize_open_algo_orders,
    normalize_position_risk_row,
)
from scripts.submit_replayed_testnet_payload import (
    DEFAULT_TESTNET_BASE_URL,
    _resolve_testnet_base_url,
)


def check_testnet_state(*, env: str, symbol: str, base_url: str = "") -> dict[str, Any]:
    resolved_env = str(env or "").strip().lower()
    target_symbol = str(symbol or "").strip().upper()
    resolved_base_url = _resolve_testnet_base_url(base_url) if base_url else DEFAULT_TESTNET_BASE_URL
    if resolved_env != "testnet":
        return {
            "ok": False,
            "env": resolved_env,
            "symbol": target_symbol,
            "base_url": resolved_base_url,
            "error_code": "env_not_testnet",
            "error_message": "env must be testnet",
        }

    api_key = str(os.getenv("BINANCE_TESTNET_API_KEY", "")).strip()
    api_secret = str(os.getenv("BINANCE_TESTNET_API_SECRET", "")).strip()
    if not api_key or not api_secret:
        return {
            "ok": False,
            "env": resolved_env,
            "symbol": target_symbol,
            "base_url": resolved_base_url,
            "error_code": "missing_testnet_api_key",
            "error_message": "missing_testnet_api_key",
        }

    client = BinanceFuturesTestnetClient(api_key=api_key, api_secret=api_secret, base_url=resolved_base_url)
    pos_resp = client.get_position_risk(symbol=target_symbol)
    open_resp = client.get_open_algo_orders(symbol=target_symbol, algo_type="CONDITIONAL")
    if not bool(pos_resp.get("ok", False)):
        return {
            "ok": False,
            "env": resolved_env,
            "symbol": target_symbol,
            "base_url": resolved_base_url,
            "error_code": str(pos_resp.get("error_code", "position_query_failed")),
            "error_message": str(pos_resp.get("error_message", "position query failed")),
        }
    if not bool(open_resp.get("ok", False)):
        return {
            "ok": False,
            "env": resolved_env,
            "symbol": target_symbol,
            "base_url": resolved_base_url,
            "error_code": str(open_resp.get("error_code", "open_algo_orders_query_failed")),
            "error_message": str(open_resp.get("error_message", "open algo orders query failed")),
        }

    position_rows = [row for row in list(pos_resp.get("response", [])) if isinstance(row, dict)]
    open_rows = [row for row in list(open_resp.get("response", [])) if isinstance(row, dict)]
    position = normalize_position_risk_row(position_rows[0] if position_rows else {"symbol": target_symbol})
    algo = normalize_open_algo_orders(open_rows)
    return build_testnet_state_result(
        target_symbol,
        position,
        algo,
        metadata={"env": resolved_env, "base_url": resolved_base_url},
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check Binance Futures testnet position/protection state")
    parser.add_argument("--env", default="testnet")
    parser.add_argument("--symbol", default="FETUSDT")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--base-url", default="")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = check_testnet_state(
        env=str(args.env or "testnet"),
        symbol=str(args.symbol or "FETUSDT"),
        base_url=str(args.base_url or ""),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return

    if not bool(result.get("ok", False)):
        print(f"env={result.get('env', '')}")
        print(f"symbol={result.get('symbol', '')}")
        print(f"base_url={result.get('base_url', '')}")
        print(f"error_code={result.get('error_code', '')}")
        print(f"error_message={result.get('error_message', '')}")
        return

    print(f"env={result.get('env', '')}")
    print(f"symbol={result.get('symbol', '')}")
    print(f"base_url={result.get('base_url', '')}")
    print(f"positionAmt={result.get('positionAmt', 0.0)}")
    print(f"entryPrice={result.get('entryPrice', 0.0)}")
    print(f"markPrice={result.get('markPrice', 0.0)}")
    print(f"openAlgoOrdersCount={result.get('openAlgoOrdersCount', 0)}")
    print(f"open_stop_market_count={result.get('open_stop_market_count', 0)}")
    print(f"open_take_profit_market_count={result.get('open_take_profit_market_count', 0)}")
    print(f"protection_status={result.get('protection_status', '')}")
    print(f"action_required={result.get('action_required', '')}")


if __name__ == "__main__":
    main()
