from __future__ import annotations

import json
from typing import Any, Mapping, Optional
from urllib import error as url_error
from urllib import parse as url_parse


_SENSITIVE_QUERY_KEYS = {
    "signature",
    "api_key",
    "apikey",
    "secret",
    "api_secret",
}
_SENSITIVE_HEADER_KEYS = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-mbx-apikey",
    "x-api-key",
}
_MAX_RESPONSE_TEXT_LENGTH = 4000


def build_http_error_from_exception(
    exc: Exception,
    *,
    request_payload: Optional[Mapping[str, Any]] = None,
    error_prefix: str = "http_request_failed",
) -> dict[str, Any]:
    request = dict(request_payload or {})
    request_url = _sanitize_url(str(request.get("url", "") or ""))
    request_path = _resolve_request_path(request=request, request_url=request_url)
    method = _resolve_method(request)

    response_text = ""
    response_json: Any = None
    http_status = _normalize_http_status(None)
    error_type = exc.__class__.__name__

    if isinstance(exc, url_error.HTTPError):
        http_status = _normalize_http_status(exc.code)
        response_text = _safe_decode_bytes(_read_exception_body(exc))
        response_json = _parse_json_text(response_text)
        url_from_exception = _sanitize_url(str(getattr(exc, "url", "") or ""))
        if url_from_exception:
            request_url = url_from_exception
            request_path = _resolve_request_path(request=request, request_url=request_url)
    elif isinstance(exc, url_error.URLError):
        response_text = str(getattr(exc, "reason", exc) or "")
    else:
        response_text = str(exc or "")

    binance_code, binance_msg = extract_binance_code_msg(
        response_json=response_json,
        response_text=response_text,
    )

    resolved_error = f"{error_prefix}:{error_type}" if error_prefix else error_type
    return {
        "ok": False,
        "error": resolved_error,
        "error_type": error_type,
        "http_status": http_status,
        "response_text": _truncate_text(response_text),
        "response_json": response_json,
        "request_url": request_url,
        "request_path": request_path,
        "method": method,
        "headers_summary": summarize_headers(request.get("headers")),
        "binance_code": binance_code,
        "binance_msg": binance_msg,
        "request": sanitize_request_payload(request),
    }


def build_http_error_from_response(
    response_payload: Mapping[str, Any],
    *,
    request_payload: Optional[Mapping[str, Any]] = None,
    default_error: str = "http_request_failed",
) -> dict[str, Any]:
    response = dict(response_payload or {})
    request = dict(request_payload or {})

    request_url = _sanitize_url(
        str(
            response.get("request_url", response.get("url", request.get("url", "")))
            or ""
        )
    )
    request_path = _resolve_request_path(request=response, request_url=request_url)
    if request_path == "":
        request_path = _resolve_request_path(request=request, request_url=request_url)
    method = _resolve_method(response) or _resolve_method(request)

    response_text = _resolve_response_text(response)
    response_json = _resolve_response_json(response, response_text=response_text)
    binance_code, binance_msg = extract_binance_code_msg(
        response_json=response_json,
        response_text=response_text,
    )

    error_text = str(response.get("error", response.get("reason", "")) or "").strip()
    error_type = str(response.get("error_type", "") or "").strip()
    if error_type == "":
        error_type = _infer_error_type(error_text)
    if error_type == "":
        error_type = "TransportError"

    if error_text == "":
        if default_error:
            error_text = f"{default_error}:{error_type}"
        else:
            error_text = error_type

    headers_payload = response.get("headers", request.get("headers"))
    if not isinstance(headers_payload, Mapping):
        headers_payload = request.get("headers")

    return {
        "ok": False,
        "error": error_text,
        "error_type": error_type,
        "http_status": _normalize_http_status(
            response.get("http_status", response.get("status_code", response.get("status")))
        ),
        "response_text": _truncate_text(response_text),
        "response_json": response_json,
        "request_url": request_url,
        "request_path": request_path,
        "method": method,
        "headers_summary": summarize_headers(headers_payload),
        "binance_code": binance_code,
        "binance_msg": binance_msg,
        "request": sanitize_request_payload(request),
    }


def sanitize_request_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(payload or {})
    return {
        "method": _resolve_method(row),
        "path": str(row.get("path", "") or ""),
        "url": _sanitize_url(str(row.get("url", "") or "")),
        "environment": str(row.get("environment", "") or ""),
        "market_type": str(row.get("market_type", "") or ""),
        "signed": bool(row.get("signed", False)),
        "headers_summary": summarize_headers(row.get("headers")),
    }


def summarize_headers(headers: Any) -> dict[str, str]:
    if not isinstance(headers, Mapping):
        return {}
    summary: dict[str, str] = {}
    for key, value in headers.items():
        header_name = str(key or "")
        if header_name == "":
            continue
        value_text = str(value or "")
        if header_name.lower() in _SENSITIVE_HEADER_KEYS:
            summary[header_name] = "<redacted>"
            continue
        summary[header_name] = _truncate_text(value_text, limit=128)
    return summary


def extract_binance_code_msg(
    *,
    response_json: Any,
    response_text: str,
) -> tuple[Any, str]:
    if isinstance(response_json, Mapping):
        code = response_json.get("code")
        msg = response_json.get("msg", response_json.get("message", ""))
        return code, str(msg or "")
    return None, ""


def _resolve_response_text(payload: Mapping[str, Any]) -> str:
    for key in ("response_text", "body", "text", "raw_text"):
        value = payload.get(key)
        if value in ("", None):
            continue
        return _safe_decode_value(value)
    value = payload.get("data")
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return _safe_decode_bytes(value)
    return ""


def _resolve_response_json(payload: Mapping[str, Any], *, response_text: str) -> Any:
    value = payload.get("response_json")
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, list):
        return list(value)
    if isinstance(value, str) and value.strip():
        parsed = _parse_json_text(value)
        if parsed is not None:
            return parsed

    data = payload.get("data")
    if isinstance(data, Mapping):
        return dict(data)
    if isinstance(data, list):
        return list(data)

    parsed_text = _parse_json_text(response_text)
    return parsed_text


def _infer_error_type(error_text: str) -> str:
    text = str(error_text or "")
    if ":" in text:
        tail = text.split(":")[-1].strip()
        if tail:
            return tail
    return ""


def _resolve_method(payload: Mapping[str, Any]) -> str:
    method = str(payload.get("method", "") or "").strip().upper()
    return method or "GET"


def _resolve_request_path(*, request: Mapping[str, Any], request_url: str) -> str:
    path = str(request.get("request_path", request.get("path", "")) or "").strip()
    if path:
        return path
    url_text = str(request_url or "").strip()
    if not url_text:
        return ""
    parsed = url_parse.urlsplit(url_text)
    return str(parsed.path or "")


def _sanitize_url(url: str) -> str:
    value = str(url or "").strip()
    if value == "":
        return ""
    parsed = url_parse.urlsplit(value)
    query_pairs = url_parse.parse_qsl(parsed.query, keep_blank_values=True)
    if not query_pairs:
        return value
    sanitized_pairs: list[tuple[str, str]] = []
    for key, raw_value in query_pairs:
        normalized_key = str(key or "")
        lowered = normalized_key.lower()
        if lowered in _SENSITIVE_QUERY_KEYS:
            sanitized_pairs.append((normalized_key, "<redacted>"))
            continue
        sanitized_pairs.append((normalized_key, str(raw_value or "")))
    sanitized_query = url_parse.urlencode(sanitized_pairs)
    return url_parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, sanitized_query, parsed.fragment))


def _normalize_http_status(value: Any) -> Optional[int]:
    if value in ("", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_json_text(value: str) -> Any:
    text = str(value or "").strip()
    if text == "":
        return None
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


def _truncate_text(value: str, *, limit: int = _MAX_RESPONSE_TEXT_LENGTH) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...(truncated)"


def _safe_decode_bytes(raw: bytes) -> str:
    if not isinstance(raw, (bytes, bytearray)):
        return ""
    try:
        return bytes(raw).decode("utf-8")
    except UnicodeDecodeError:
        return bytes(raw).decode("utf-8", errors="replace")


def _safe_decode_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray)):
        return _safe_decode_bytes(bytes(value))
    return str(value or "")


def _read_exception_body(exc: url_error.HTTPError) -> bytes:
    try:
        body = exc.read()
    except Exception:
        return b""
    return body if isinstance(body, (bytes, bytearray)) else b""
