from __future__ import annotations

from typing import Any


def build_account_next_actions(
    *,
    category: str,
    market_type: str,
    account_path: str,
    http_status: Any = None,
    binance_code: Any = None,
    binance_msg: str = "",
) -> list[str]:
    actions: list[str] = []

    def add(action: str) -> None:
        key = str(action or "").strip()
        if key and key not in actions:
            actions.append(key)

    category_key = str(category or "").strip()
    market_key = str(market_type or "").strip().lower()
    path = str(account_path or "").strip()
    status_text = str(http_status or "").strip()
    code_text = str(binance_code or "").strip()
    msg_text = str(binance_msg or "").lower()

    if code_text or msg_text:
        add("inspect_binance_code")

    if category_key in {"account_auth_error", "account_permission_error"}:
        add("inspect_account_permissions")

    if (
        category_key == "account_permission_error"
        or "permission" in msg_text
        or "not authorized" in msg_text
    ):
        add("inspect_account_permissions")

    if "ip" in msg_text or "whitelist" in msg_text:
        add("inspect_ip_whitelist")

    if category_key in {
        "account_endpoint_error",
        "spot_account_error",
        "futures_account_error",
        "account_unexpected_payload_error",
    }:
        add("inspect_account_endpoint")

    market_type_mismatch = (
        (market_key == "futures" and path.startswith("/api/"))
        or (market_key == "spot" and path.startswith("/fapi/"))
    )
    if market_type_mismatch:
        add("inspect_market_type_selection")

    if category_key in {"spot_account_error", "futures_account_error"}:
        add("inspect_market_type_selection")

    if market_key == "spot":
        add("retry_spot_account_probe")
    if market_key == "futures":
        add("retry_futures_account_probe")

    if (
        "testnet" in msg_text and "account" in msg_text
    ) or "futures account" in msg_text or "spot account" in msg_text or "account type" in msg_text:
        add("inspect_testnet_account_type")

    # Status/code hints for endpoint/auth routing.
    if status_text in {"404", "405"}:
        add("inspect_account_endpoint")
    if status_text == "403":
        add("inspect_account_permissions")

    add("retry_testnet_preflight_only")
    add("do_not_start_live")

    return actions
