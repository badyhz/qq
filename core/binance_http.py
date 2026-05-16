from __future__ import annotations

import json
import hashlib
from typing import Any, Callable, Optional
from urllib import parse
from urllib import request as urllib_request

from core.binance_endpoints import build_binance_url
from core.binance_signing import sign_binance_params
from core.http_error_parser import (
    build_http_error_from_exception,
    build_http_error_from_response,
    sanitize_request_payload,
)

Transport = Callable[[dict[str, Any]], Any]


def build_public_request(
    *,
    method: str,
    path: str,
    environment: str,
    market_type: str = "spot",
    params: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    normalized_method = str(method or "GET").strip().upper()
    normalized_path = str(path or "").strip()
    normalized_params = dict(params or {})
    query_string = parse.urlencode({k: v for k, v in normalized_params.items() if v not in (None, "")})
    url = build_binance_url(environment=environment, path=normalized_path, market_type=market_type)
    if query_string:
        url = f"{url}?{query_string}"
    return {
        "ok": True,
        "signed": False,
        "method": normalized_method,
        "path": normalized_path,
        "url": url,
        "params": normalized_params,
        "headers": dict(headers or {}),
        "environment": str(environment or "live"),
        "market_type": str(market_type or "spot"),
        "query_string": query_string,
    }


def build_signed_request(
    *,
    method: str,
    path: str,
    environment: str,
    market_type: str = "spot",
    api_key: str,
    api_secret: str,
    params: Optional[dict[str, Any]] = None,
    recv_window: int = 5000,
    timestamp_ms: Optional[int] = None,
) -> dict[str, Any]:
    if str(api_key or "") == "" or str(api_secret or "") == "":
        return {
            "ok": False,
            "error": "missing_api_credentials",
            "method": str(method or "GET").strip().upper(),
            "path": str(path or "").strip(),
            "environment": str(environment or "live"),
            "market_type": str(market_type or "spot"),
            "params": dict(params or {}),
        }

    signed = sign_binance_params(
        params or {},
        api_secret=str(api_secret),
        include_timestamp=True,
        timestamp_ms=timestamp_ms,
        recv_window=recv_window,
    )
    normalized_method = str(method or "GET").strip().upper()
    normalized_path = str(path or "").strip()
    canonical_query_string = str(signed.get("canonical_query_string", ""))
    signature = str(signed.get("signature", ""))
    final_query_string = canonical_query_string
    if signature:
        final_query_string = (
            f"{canonical_query_string}&signature={signature}"
            if canonical_query_string
            else f"signature={signature}"
        )
    url = build_binance_url(environment=environment, path=normalized_path, market_type=market_type)
    if final_query_string:
        url = f"{url}?{final_query_string}"
    signed_param_keys = [str(item) for item in list(signed.get("signed_param_keys", [])) if str(item)]
    canonical_query_sha256 = str(signed.get("canonical_query_sha256", ""))
    if canonical_query_sha256 == "" and canonical_query_string:
        canonical_query_sha256 = hashlib.sha256(canonical_query_string.encode("utf-8")).hexdigest()
    return {
        "ok": True,
        "signed": True,
        "method": normalized_method,
        "path": normalized_path,
        "url": url,
        "params": dict(signed.get("params", {})),
        "headers": {"X-MBX-APIKEY": str(api_key)},
        "environment": str(environment or "live"),
        "market_type": str(market_type or "spot"),
        "query_string": "<redacted>",
        "canonical_query_sha256": canonical_query_sha256,
        "signed_param_keys": signed_param_keys,
        "request_path": normalized_path,
    }


def build_urllib_passthrough_transport(*, timeout_seconds: float = 5.0) -> Transport:
    timeout = float(timeout_seconds)

    def _transport(payload: dict[str, Any]) -> dict[str, Any]:
        row = dict(payload or {})
        url = str(row.get("url", "")).strip()
        if url == "":
            return {"ok": False, "error": "invalid_request_payload:missing_url"}
        method = str(row.get("method", "GET")).strip().upper() or "GET"
        req = urllib_request.Request(url, method=method)
        for key, value in dict(row.get("headers", {})).items():
            req.add_header(str(key), str(value))
        with urllib_request.urlopen(req, timeout=timeout) as response:  # pragma: no cover - network path
            body = response.read()
            response_text = body.decode("utf-8", errors="replace")
            response_json = None
            if response_text.strip() != "":
                try:
                    response_json = json.loads(response_text)
                except (TypeError, ValueError):
                    response_json = None
            payload_data: Any = response_json if response_json is not None else response_text
            return {
                "ok": True,
                "data": payload_data,
                "http_status": int(getattr(response, "status", 0) or 0) or None,
                "response_text": response_text,
                "response_json": response_json,
                "url": str(getattr(response, "url", url) or url),
                "path": str(row.get("path", "")),
                "method": method,
            }

    return _transport


def _normalize_failed_response(
    *,
    request_payload: dict[str, Any],
    result_payload: dict[str, Any],
) -> dict[str, Any]:
    return build_http_error_from_response(
        result_payload,
        request_payload=request_payload,
        default_error="http_request_failed",
    )


def send_binance_request(request_payload: dict[str, Any], *, transport: Optional[Transport] = None) -> dict[str, Any]:
    payload = dict(request_payload or {})
    if not payload.get("ok", True):
        return _normalize_failed_response(request_payload=payload, result_payload=payload)

    if callable(transport):
        try:
            result = transport(payload)
        except Exception as exc:  # pragma: no cover - defensive path
            return build_http_error_from_exception(
                exc,
                request_payload=payload,
                error_prefix="transport_exception",
            )
        if isinstance(result, dict):
            if result.get("ok", True) is False:
                return _normalize_failed_response(request_payload=payload, result_payload=result)
            merged = dict(payload)
            merged.update(result)
            merged.setdefault("ok", True)
            return merged
        return {"ok": True, "request": sanitize_request_payload(payload), "data": result}

    try:
        default_transport = build_urllib_passthrough_transport()
    except Exception as exc:  # pragma: no cover - defensive path
        return build_http_error_from_exception(
            exc,
            request_payload=payload,
            error_prefix="default_transport_build_failed",
        )
    try:
        result = default_transport(payload)
    except Exception as exc:  # pragma: no cover - defensive path
        return build_http_error_from_exception(
            exc,
            request_payload=payload,
            error_prefix="http_request_failed",
        )
    if isinstance(result, dict):
        if result.get("ok", True) is False:
            return _normalize_failed_response(request_payload=payload, result_payload=result)
        merged = dict(payload)
        merged.update(result)
        merged.setdefault("ok", True)
        return merged
    return {"ok": True, "request": sanitize_request_payload(payload), "data": result}
