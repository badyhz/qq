from __future__ import annotations

import time
from typing import Any, Optional


def local_timestamp_ms() -> int:
    return int(time.time() * 1000)


def parse_server_time_ms(payload: Any) -> Optional[int]:
    row = payload
    if isinstance(row, dict) and isinstance(row.get("data"), dict):
        row = row.get("data")
    if not isinstance(row, dict):
        return None
    value = row.get("serverTime", row.get("server_time", row.get("server_time_ms")))
    if value in ("", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def compute_server_time_offset_ms(*, server_time_ms: int, local_time_ms: int) -> int:
    return int(server_time_ms) - int(local_time_ms)


def is_timestamp_ahead_error(*, binance_code: Any = None, message: str = "") -> bool:
    text = str(message or "").lower()
    if str(binance_code) == "-1021":
        return True
    if "timestamp" in text and "ahead" in text and "server" in text:
        return True
    return False
