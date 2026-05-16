from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlencode


def normalize_query_params(params: dict[str, Any] | None) -> dict[str, str]:
    row = dict(params or {})
    normalized: dict[str, str] = {}
    for key in sorted(row.keys()):
        value = row.get(key)
        if value in (None, ""):
            continue
        if isinstance(value, bool):
            normalized[str(key)] = "true" if value else "false"
        else:
            normalized[str(key)] = str(value)
    return normalized


def build_query_string(params: dict[str, Any] | None) -> str:
    normalized = normalize_query_params(params)
    return urlencode(list(normalized.items()))


def sign_binance_query(query_string: str, api_secret: str) -> str:
    secret = str(api_secret or "")
    if secret == "":
        raise ValueError("missing_api_secret")
    payload = str(query_string or "")
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def sign_binance_params(
    params: dict[str, Any] | None,
    *,
    api_secret: str,
    include_timestamp: bool = True,
    timestamp_ms: int | None = None,
    recv_window: int = 5000,
) -> dict[str, Any]:
    base_params = normalize_query_params(params)
    if include_timestamp and "timestamp" not in base_params:
        base_params["timestamp"] = str(int(timestamp_ms) if timestamp_ms is not None else current_timestamp_ms())
    if recv_window > 0 and "recvWindow" not in base_params:
        base_params["recvWindow"] = str(int(recv_window))
    canonical_params = normalize_query_params(base_params)
    canonical_query_string = urlencode(list(canonical_params.items()))
    signature = sign_binance_query(canonical_query_string, api_secret)
    signed_params = dict(canonical_params)
    signed_params["signature"] = signature
    canonical_query_sha256 = hashlib.sha256(canonical_query_string.encode("utf-8")).hexdigest()
    return {
        "params": signed_params,
        "canonical_query_string": canonical_query_string,
        "query_string": canonical_query_string,
        "signature": signature,
        "signed_param_keys": list(canonical_params.keys()),
        "canonical_query_sha256": canonical_query_sha256,
    }


def current_timestamp_ms() -> int:
    return int(time.time() * 1000)
