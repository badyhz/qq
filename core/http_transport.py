from __future__ import annotations

import json
from typing import Any, Callable
from urllib import request


def build_urllib_transport(*, timeout_seconds: float = 5.0) -> Callable[[dict[str, Any]], dict[str, Any]]:
    timeout = float(timeout_seconds)

    def _transport(payload: dict[str, Any]) -> dict[str, Any]:
        row = dict(payload or {})
        url = str(row.get("url", "")).strip()
        if not url:
            return {"ok": False, "error": "invalid_request_payload:missing_url"}
        method = str(row.get("method", "GET")).strip().upper() or "GET"
        try:
            req = request.Request(url, method=method)
            for key, value in dict(row.get("headers", {})).items():
                req.add_header(str(key), str(value))
            with request.urlopen(req, timeout=timeout) as response:  # pragma: no cover - network path
                raw = response.read().decode("utf-8")
                data = json.loads(raw) if raw else {}
            return {"ok": True, "data": data}
        except Exception as exc:  # pragma: no cover - network path
            return {
                "ok": False,
                "error": f"http_request_failed:{exc.__class__.__name__}",
            }

    return _transport
