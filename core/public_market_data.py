from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import time
from typing import Any, Optional
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen


def normalize_kline_interval(interval: Any) -> str:
    value = str(interval or "").strip()
    return value or "5m"


def normalize_binance_klines_payload(
    *,
    payload: Any,
    symbol: str,
    timeframe: str,
) -> dict[str, Any]:
    resolved_symbol = str(symbol or "").strip().upper()
    resolved_timeframe = normalize_kline_interval(timeframe)
    raw_rows = payload
    if isinstance(payload, dict):
        if isinstance(payload.get("klines"), list):
            raw_rows = payload.get("klines")
        elif isinstance(payload.get("data"), list):
            raw_rows = payload.get("data")

    if not isinstance(raw_rows, list):
        return {
            "success": False,
            "error": "invalid_kline_payload",
            "symbol": resolved_symbol,
            "timeframe": resolved_timeframe,
            "klines": [],
        }
    if len(raw_rows) == 0:
        return {
            "success": False,
            "error": "empty_klines",
            "symbol": resolved_symbol,
            "timeframe": resolved_timeframe,
            "klines": [],
        }

    rows: list[dict[str, Any]] = []
    for item in raw_rows:
        normalized = normalize_binance_kline_row(
            row=item,
            symbol=resolved_symbol,
            timeframe=resolved_timeframe,
        )
        if normalized is None:
            continue
        rows.append(normalized)
    if len(rows) == 0:
        return {
            "success": False,
            "error": "invalid_kline_payload",
            "symbol": resolved_symbol,
            "timeframe": resolved_timeframe,
            "klines": [],
        }
    return {
        "success": True,
        "error": "",
        "symbol": resolved_symbol,
        "timeframe": resolved_timeframe,
        "klines": rows,
    }


def normalize_binance_kline_row(
    *,
    row: Any,
    symbol: str,
    timeframe: str,
) -> Optional[dict[str, Any]]:
    if not isinstance(row, (list, tuple)):
        return None
    if len(row) < 9:
        return None
    open_time = _to_int(row[0], default=0)
    open_price = _to_float(row[1], default=0.0)
    high_price = _to_float(row[2], default=0.0)
    low_price = _to_float(row[3], default=0.0)
    close_price = _to_float(row[4], default=0.0)
    volume = _to_float(row[5], default=0.0)
    close_time = _to_int(row[6], default=0)
    quote_volume = _to_float(row[7], default=0.0)
    trade_count = _to_int(row[8], default=0)
    taker_buy_base_volume = _to_float(row[9], default=0.0) if len(row) > 9 else 0.0
    taker_buy_quote_volume = _to_float(row[10], default=0.0) if len(row) > 10 else 0.0
    taker_buy_ratio = (taker_buy_quote_volume / quote_volume) if quote_volume > 0 else 0.0
    if open_time <= 0 and close_time <= 0:
        return None
    return {
        "symbol": str(symbol or "").strip().upper(),
        "timeframe": normalize_kline_interval(timeframe),
        "timestamp": open_time if open_time > 0 else _now_ms(),
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": volume,
        "close_time": close_time,
        "quote_volume": quote_volume,
        "trade_count": trade_count,
        "taker_buy_base_volume": taker_buy_base_volume,
        "taker_buy_quote_volume": taker_buy_quote_volume,
        "taker_buy_ratio": taker_buy_ratio,
    }


def fetch_binance_order_flow_public(
    *,
    symbol: str,
    timeframe: str,
    limit: int = 300,
    timeout_sec: float = 10.0,
    futures_base_url: str = "https://fapi.binance.com",
    start_time_ms: Optional[int] = None,
    end_time_ms: Optional[int] = None,
    target_rows: Optional[int] = None,
) -> dict[str, Any]:
    resolved_symbol = str(symbol or "").strip().upper()
    resolved_tf = normalize_kline_interval(timeframe)
    resolved_limit = max(1, int(limit))
    resolved_target_rows = max(resolved_limit, _to_int(target_rows, default=resolved_limit))
    resolved_start_ms = _to_int(start_time_ms, default=0)
    resolved_end_ms = _to_int(end_time_ms, default=0)
    if resolved_end_ms <= 0:
        resolved_end_ms = _now_ms()
    interval_ms = _interval_to_ms(resolved_tf)
    warnings: list[str] = []

    oi_fetch = _fetch_paginated_source(
        base_url=futures_base_url,
        path="/futures/data/openInterestHist",
        base_query={
            "symbol": resolved_symbol,
            "period": resolved_tf,
        },
        normalize_rows_fn=_normalize_open_interest_rows,
        source_limit=max(5, min(500, resolved_limit)),
        target_rows=resolved_target_rows + 1,
        start_time_ms=resolved_start_ms,
        end_time_ms=resolved_end_ms,
        timeout_sec=timeout_sec,
    )
    oi_rows = list(oi_fetch.get("rows", []))
    oi_status = str(oi_fetch.get("status", "failed"))
    oi_error = str(oi_fetch.get("error", "") or "")
    if oi_status == "failed":
        warnings.append("oi_fetch_failed")

    taker_fetch = _fetch_paginated_source(
        base_url=futures_base_url,
        path="/futures/data/takerlongshortRatio",
        base_query={
            "symbol": resolved_symbol,
            "period": resolved_tf,
        },
        normalize_rows_fn=_normalize_taker_rows,
        source_limit=max(5, min(500, resolved_limit)),
        target_rows=resolved_target_rows,
        start_time_ms=resolved_start_ms,
        end_time_ms=resolved_end_ms,
        timeout_sec=timeout_sec,
    )
    taker_rows = list(taker_fetch.get("rows", []))
    taker_status = str(taker_fetch.get("status", "failed"))
    taker_error = str(taker_fetch.get("error", "") or "")
    if taker_status == "failed":
        warnings.append("taker_fetch_failed")

    funding_fetch = _fetch_paginated_source(
        base_url=futures_base_url,
        path="/fapi/v1/fundingRate",
        base_query={
            "symbol": resolved_symbol,
        },
        normalize_rows_fn=_normalize_funding_rows,
        source_limit=max(5, min(1000, resolved_limit)),
        target_rows=max(200, min(resolved_target_rows, 1000)),
        start_time_ms=resolved_start_ms,
        end_time_ms=resolved_end_ms,
        timeout_sec=timeout_sec,
    )
    funding_rows = list(funding_fetch.get("rows", []))
    funding_status = str(funding_fetch.get("status", "failed"))
    funding_error = str(funding_fetch.get("error", "") or "")
    if funding_status == "failed":
        warnings.append("funding_fetch_failed")

    statuses = [oi_status, taker_status, funding_status]
    if "ok" in statuses:
        status = "ok"
    elif "failed" in statuses:
        status = "failed"
    else:
        status = "empty"
    error_messages = [msg for msg in [oi_error, taker_error, funding_error] if msg]
    coverage = _build_order_flow_coverage(
        oi_rows=oi_rows,
        taker_rows=taker_rows,
        funding_rows=funding_rows,
        kline_first_timestamp=resolved_start_ms,
        kline_last_timestamp=resolved_end_ms,
        timeframe_ms=interval_ms,
    )
    if str(coverage.get("coverage_status", "")) in {"partial", "insufficient"}:
        warnings.append(f"coverage_{coverage.get('coverage_status')}")

    return {
        "success": status == "ok",
        "status": status,
        "error": " | ".join(error_messages),
        "symbol": resolved_symbol,
        "timeframe": resolved_tf,
        "order_flow_rows": {
            "oi": oi_rows,
            "taker": taker_rows,
            "funding": funding_rows,
        },
        "sources": {
            "oi": {"status": oi_status, "rows": oi_rows, "error": oi_error},
            "taker": {"status": taker_status, "rows": taker_rows, "error": taker_error},
            "funding": {"status": funding_status, "rows": funding_rows, "error": funding_error},
        },
        "coverage": coverage,
        "warnings": warnings,
    }


def fetch_binance_futures_exchange_info_public(
    *,
    symbol: Optional[str] = None,
    futures_base_url: str = "https://fapi.binance.com",
    timeout_sec: float = 10.0,
) -> dict[str, Any]:
    resolved_symbol = str(symbol or "").strip().upper()
    query: dict[str, str] = {}
    if resolved_symbol:
        query["symbol"] = resolved_symbol
    resp = _http_json_with_retry(
        base_url=futures_base_url,
        path="/fapi/v1/exchangeInfo",
        query=query,
        timeout_sec=timeout_sec,
        retries_on_429=2,
    )
    if not bool(resp.get("ok", False)):
        return {
            "success": False,
            "status": "failed",
            "precision_status": "exchange_info_unavailable_fallback",
            "error": str(resp.get("error", "") or "exchange_info_fetch_failed"),
            "symbols": {},
            "raw": {},
        }
    payload = resp.get("payload", {})
    if not isinstance(payload, dict):
        return {
            "success": False,
            "status": "failed",
            "precision_status": "exchange_info_unavailable_fallback",
            "error": "invalid_exchange_info_payload",
            "symbols": {},
            "raw": payload,
        }
    symbols_payload = payload.get("symbols", [])
    if not isinstance(symbols_payload, list):
        symbols_payload = []
    normalized: dict[str, Any] = {}
    for item in symbols_payload:
        row = _normalize_futures_exchange_symbol(item)
        if row is None:
            continue
        sym = str(row.get("symbol", "")).strip().upper()
        if not sym:
            continue
        normalized[sym] = row
    if resolved_symbol and resolved_symbol not in normalized:
        return {
            "success": False,
            "status": "empty",
            "precision_status": "exchange_info_unavailable_fallback",
            "error": f"symbol_not_found:{resolved_symbol}",
            "symbols": {},
            "raw": payload,
        }
    return {
        "success": len(normalized) > 0,
        "status": "ok" if len(normalized) > 0 else "empty",
        "precision_status": "exchange_info_ok" if len(normalized) > 0 else "exchange_info_unavailable_fallback",
        "error": "",
        "symbols": normalized,
        "raw": payload,
    }


def fetch_binance_spot_klines_public(
    *,
    symbol: str,
    interval: str,
    limit: int = 500,
    timeout_sec: float = 10.0,
    spot_base_url: str = "https://api.binance.com",
    end_time_ms: Optional[int] = None,
    progress: bool = False,
    progress_prefix: str = "",
) -> dict[str, Any]:
    resolved_symbol = str(symbol or "").strip().upper()
    resolved_interval = normalize_kline_interval(interval)
    requested_limit = max(1, int(limit))
    page_size = min(1000, requested_limit)
    max_pages = max(1, int(math.ceil(requested_limit / 1000.0)) + 5)
    warnings: list[str] = []
    all_rows: list[dict[str, Any]] = []
    seen_timestamps: set[int] = set()
    pages_fetched = 0
    duplicate_pages = 0
    cursor_end_ms = _to_int(end_time_ms, default=0)
    if cursor_end_ms <= 0:
        cursor_end_ms = _now_ms()
    started_at = time.monotonic()

    while pages_fetched < max_pages and len(all_rows) < requested_limit:
        pages_fetched += 1
        query = {
            "symbol": resolved_symbol,
            "interval": resolved_interval,
            "limit": str(page_size),
            "endTime": str(cursor_end_ms),
        }
        resp = _http_json_with_retry(
            base_url=spot_base_url,
            path="/api/v3/klines",
            query=query,
            timeout_sec=timeout_sec,
            retries_on_429=2,
        )
        if not bool(resp.get("ok", False)):
            warnings.append(f"kline_fetch_failed_page_{pages_fetched}:{resp.get('error', '')}")
            break
        payload = resp.get("payload", [])
        if not isinstance(payload, list) or len(payload) == 0:
            warnings.append(f"kline_fetch_empty_page_{pages_fetched}")
            break
        normalized = normalize_binance_klines_payload(
            payload=payload,
            symbol=resolved_symbol,
            timeframe=resolved_interval,
        )
        page_rows = list(normalized.get("klines", [])) if bool(normalized.get("success", False)) else []
        if len(page_rows) == 0:
            warnings.append(f"kline_fetch_invalid_payload_page_{pages_fetched}")
            break
        page_rows.sort(key=lambda row: _to_int(row.get("timestamp"), default=0))
        before_count = len(all_rows)
        for row in page_rows:
            ts = _to_int(row.get("timestamp"), default=0)
            if ts <= 0 or ts in seen_timestamps:
                continue
            seen_timestamps.add(ts)
            all_rows.append(row)
        added = len(all_rows) - before_count
        if progress:
            elapsed = time.monotonic() - started_at
            prefix = str(progress_prefix or "")
            print(
                f"progress kline_fetch {prefix}symbol={resolved_symbol} page={pages_fetched} "
                f"rows={len(page_rows)} total_rows={len(all_rows)} elapsed={elapsed:.2f}s",
                flush=True,
            )
        if added == 0:
            duplicate_pages += 1
            warnings.append(f"kline_page_no_new_rows:{pages_fetched}")
            if duplicate_pages >= 2:
                warnings.append("kline_pagination_stopped_no_growth")
                break
        else:
            duplicate_pages = 0

        earliest_open_time = _to_int(page_rows[0].get("timestamp"), default=0)
        if earliest_open_time <= 0:
            warnings.append(f"kline_page_invalid_earliest_ts:{pages_fetched}")
            break
        next_end = earliest_open_time - 1
        if next_end >= cursor_end_ms:
            warnings.append("kline_pagination_stopped_non_decreasing_cursor")
            break
        cursor_end_ms = next_end
        time.sleep(0.1)

    all_rows.sort(key=lambda row: _to_int(row.get("timestamp"), default=0))
    if len(all_rows) > requested_limit:
        all_rows = all_rows[-requested_limit:]
    if len(all_rows) < requested_limit:
        warnings.append(f"kline_rows_less_than_requested:requested={requested_limit}:actual={len(all_rows)}")
    time_range = _build_time_range(all_rows)
    return {
        "success": len(all_rows) > 0,
        "error": "" if len(all_rows) > 0 else "empty_klines",
        "symbol": resolved_symbol,
        "timeframe": resolved_interval,
        "requested_limit": requested_limit,
        "actual_rows": len(all_rows),
        "pages_fetched": pages_fetched,
        "klines": all_rows,
        "kline_first_timestamp": time_range["first"],
        "kline_last_timestamp": time_range["last"],
        "warnings": warnings,
    }


def fetch_binance_spot_klines_public_since(
    *,
    symbol: str,
    interval: str,
    start_time_ms: int,
    limit: int = 500,
    timeout_sec: float = 10.0,
    spot_base_url: str = "https://api.binance.com",
    end_time_ms: Optional[int] = None,
) -> dict[str, Any]:
    resolved_symbol = str(symbol or "").strip().upper()
    resolved_interval = normalize_kline_interval(interval)
    requested_limit = max(1, int(limit))
    page_size = min(1000, requested_limit)
    interval_ms = _interval_to_ms(resolved_interval)
    warnings: list[str] = []
    all_rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    cursor_start = max(1, _to_int(start_time_ms, default=1))
    resolved_end_ms = _to_int(end_time_ms, default=0)
    if resolved_end_ms <= 0:
        resolved_end_ms = 0
    max_pages = max(1, int(math.ceil(requested_limit / 1000.0)) + 5)
    pages_fetched = 0

    while pages_fetched < max_pages and len(all_rows) < requested_limit:
        pages_fetched += 1
        query = {
            "symbol": resolved_symbol,
            "interval": resolved_interval,
            "limit": str(page_size),
            "startTime": str(cursor_start),
        }
        if resolved_end_ms > 0:
            query["endTime"] = str(resolved_end_ms)
        resp = _http_json_with_retry(
            base_url=spot_base_url,
            path="/api/v3/klines",
            query=query,
            timeout_sec=timeout_sec,
            retries_on_429=2,
        )
        if not bool(resp.get("ok", False)):
            warnings.append(f"kline_fetch_failed_page_{pages_fetched}:{resp.get('error', '')}")
            break
        payload = resp.get("payload", [])
        if not isinstance(payload, list) or len(payload) == 0:
            break
        normalized = normalize_binance_klines_payload(
            payload=payload,
            symbol=resolved_symbol,
            timeframe=resolved_interval,
        )
        page_rows = list(normalized.get("klines", [])) if bool(normalized.get("success", False)) else []
        if len(page_rows) == 0:
            warnings.append(f"kline_fetch_invalid_payload_page_{pages_fetched}")
            break
        page_rows.sort(key=lambda row: _to_int(row.get("timestamp"), default=0))
        before = len(all_rows)
        for row in page_rows:
            ts = _to_int(row.get("timestamp"), default=0)
            if ts <= 0 or ts in seen:
                continue
            if resolved_end_ms > 0 and ts > resolved_end_ms:
                continue
            seen.add(ts)
            all_rows.append(row)
        if len(all_rows) == before:
            warnings.append("kline_since_no_new_rows")
            break
        next_start = _to_int(page_rows[-1].get("timestamp"), default=0) + max(1, interval_ms)
        if next_start <= cursor_start:
            warnings.append("kline_since_non_increasing_cursor")
            break
        cursor_start = next_start
        time.sleep(0.1)

    all_rows.sort(key=lambda row: _to_int(row.get("timestamp"), default=0))
    if len(all_rows) > requested_limit:
        all_rows = all_rows[:requested_limit]
    if len(all_rows) < requested_limit:
        warnings.append(f"kline_rows_less_than_requested:requested={requested_limit}:actual={len(all_rows)}")
    time_range = _build_time_range(all_rows)
    return {
        "success": len(all_rows) > 0,
        "error": "" if len(all_rows) > 0 else "empty_klines",
        "symbol": resolved_symbol,
        "timeframe": resolved_interval,
        "requested_limit": requested_limit,
        "actual_rows": len(all_rows),
        "pages_fetched": pages_fetched,
        "klines": all_rows,
        "kline_first_timestamp": time_range["first"],
        "kline_last_timestamp": time_range["last"],
        "warnings": warnings,
    }


def _to_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _http_json(
    *,
    base_url: str,
    path: str,
    query: dict[str, str],
    timeout_sec: float,
) -> dict[str, Any]:
    url = f"{str(base_url).rstrip('/')}{path}?{urlencode(query)}"
    try:
        with urlopen(url, timeout=float(timeout_sec)) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return {"ok": True, "payload": payload, "error": ""}
    except Exception as exc:
        return {"ok": False, "payload": [], "error": f"{exc.__class__.__name__}:{exc}"}


def _http_json_with_retry(
    *,
    base_url: str,
    path: str,
    query: dict[str, str],
    timeout_sec: float,
    retries_on_429: int = 2,
) -> dict[str, Any]:
    attempts = 0
    while True:
        attempts += 1
        url = f"{str(base_url).rstrip('/')}{path}?{urlencode(query)}"
        try:
            with urlopen(url, timeout=float(timeout_sec)) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                return {"ok": True, "payload": payload, "error": "", "status_code": getattr(resp, "status", None)}
        except HTTPError as exc:
            status = int(getattr(exc, "code", 0) or 0)
            if status == 429 and attempts <= retries_on_429 + 1:
                time.sleep(0.3 * attempts)
                continue
            return {"ok": False, "payload": [], "error": f"HTTPError:{status}:{exc}", "status_code": status}
        except Exception as exc:
            return {"ok": False, "payload": [], "error": f"{exc.__class__.__name__}:{exc}", "status_code": None}


def _build_time_range(rows: list[dict[str, Any]]) -> dict[str, Optional[int]]:
    timestamps = [_to_int(row.get("timestamp"), default=0) for row in list(rows or []) if isinstance(row, dict)]
    timestamps = [ts for ts in timestamps if ts > 0]
    if not timestamps:
        return {"first": None, "last": None}
    return {"first": min(timestamps), "last": max(timestamps)}


def _normalize_open_interest_rows(rows: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        ts = _to_int(item.get("timestamp"), default=0)
        if ts <= 0:
            continue
        out.append(
            {
                "timestamp": ts,
                "open_interest": _to_float(item.get("sumOpenInterest", item.get("openInterest", 0.0)), default=0.0),
            }
        )
    return out


def _normalize_taker_rows(rows: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        ts = _to_int(item.get("timestamp"), default=0)
        if ts <= 0:
            continue
        buy = _to_float(item.get("buyVol", item.get("takerBuyVolValue", 0.0)), default=0.0)
        sell = _to_float(item.get("sellVol", item.get("takerSellVolValue", 0.0)), default=0.0)
        ratio = (buy / (buy + sell)) if (buy + sell) > 0 else 0.0
        out.append(
            {
                "timestamp": ts,
                "taker_buy_ratio": ratio,
                "taker_buy_volume": buy,
                "taker_sell_volume": sell,
            }
        )
    return out


def _normalize_funding_rows(rows: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        ts = _to_int(item.get("fundingTime"), default=0)
        if ts <= 0:
            continue
        out.append(
            {
                "timestamp": ts,
                "funding_rate": _to_float(item.get("fundingRate", 0.0), default=0.0),
            }
        )
    return out


def _normalize_futures_exchange_symbol(item: Any) -> Optional[dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    symbol = str(item.get("symbol", "")).strip().upper()
    if not symbol:
        return None
    price_tick_size = 0.0
    quantity_step_size = 0.0
    min_qty = 0.0
    max_qty = 0.0
    min_notional = 0.0
    for flt in list(item.get("filters", [])):
        if not isinstance(flt, dict):
            continue
        flt_type = str(flt.get("filterType", "")).strip().upper()
        if flt_type == "PRICE_FILTER":
            price_tick_size = _to_float(flt.get("tickSize", 0.0), default=0.0)
        elif flt_type == "LOT_SIZE":
            quantity_step_size = _to_float(flt.get("stepSize", 0.0), default=0.0)
            min_qty = _to_float(flt.get("minQty", 0.0), default=0.0)
            max_qty = _to_float(flt.get("maxQty", 0.0), default=0.0)
        elif flt_type in {"MIN_NOTIONAL", "NOTIONAL"}:
            min_notional = _to_float(
                flt.get("notional", flt.get("minNotional", 0.0)),
                default=min_notional,
            )
    return {
        "symbol": symbol,
        "price_tick_size": price_tick_size,
        "quantity_step_size": quantity_step_size,
        "min_qty": min_qty,
        "max_qty": max_qty,
        "min_notional": min_notional,
        "price_precision": _to_int(item.get("pricePrecision", 0), default=0),
        "quantity_precision": _to_int(item.get("quantityPrecision", 0), default=0),
        "contract_type": str(item.get("contractType", "")).strip(),
        "status": str(item.get("status", "")).strip(),
    }


def _fetch_paginated_source(
    *,
    base_url: str,
    path: str,
    base_query: dict[str, str],
    normalize_rows_fn,
    source_limit: int,
    target_rows: int,
    start_time_ms: int,
    end_time_ms: int,
    timeout_sec: float,
) -> dict[str, Any]:
    resolved_source_limit = max(1, int(source_limit))
    resolved_target_rows = max(1, int(target_rows))
    cursor_end = int(end_time_ms) if int(end_time_ms) > 0 else _now_ms()
    start_ms = int(start_time_ms) if int(start_time_ms) > 0 else 0
    aggregated: list[dict[str, Any]] = []
    seen: set[int] = set()
    last_error = ""
    page_count = 0
    max_pages = max(2, min(24, (resolved_target_rows // max(50, resolved_source_limit)) + 4))

    while page_count < max_pages:
        page_count += 1
        query = dict(base_query)
        query["limit"] = str(resolved_source_limit)
        if start_ms > 0:
            query["startTime"] = str(start_ms)
        query["endTime"] = str(cursor_end)
        resp = _http_json(
            base_url=base_url,
            path=path,
            query=query,
            timeout_sec=timeout_sec,
        )
        if not bool(resp.get("ok", False)):
            last_error = str(resp.get("error", "") or "")
            break
        payload = resp.get("payload", [])
        if not isinstance(payload, list) or len(payload) == 0:
            break
        rows = list(normalize_rows_fn(list(payload)))
        if len(rows) == 0:
            break
        rows.sort(key=lambda item: _to_int(item.get("timestamp"), default=0))
        for row in rows:
            ts = _to_int(row.get("timestamp"), default=0)
            if ts <= 0 or ts in seen:
                continue
            seen.add(ts)
            aggregated.append(row)
        if len(aggregated) >= resolved_target_rows and start_ms <= 0:
            break
        min_ts = _to_int(rows[0].get("timestamp"), default=0)
        if min_ts <= 0:
            break
        if start_ms > 0 and min_ts <= start_ms:
            break
        next_end = min_ts - 1
        if next_end >= cursor_end:
            break
        cursor_end = next_end

    aggregated.sort(key=lambda item: _to_int(item.get("timestamp"), default=0))
    if len(aggregated) > resolved_target_rows:
        aggregated = aggregated[-resolved_target_rows:]
    if len(aggregated) > 0:
        return {"status": "ok", "rows": aggregated, "error": last_error}
    if last_error:
        return {"status": "failed", "rows": [], "error": last_error}
    return {"status": "empty", "rows": [], "error": ""}


def _interval_to_ms(interval: str) -> int:
    text = str(interval or "5m").strip().lower()
    if not text:
        return 5 * 60 * 1000
    unit = text[-1]
    value = _to_int(text[:-1], default=1)
    if unit == "m":
        return max(1, value) * 60 * 1000
    if unit == "h":
        return max(1, value) * 60 * 60 * 1000
    if unit == "d":
        return max(1, value) * 24 * 60 * 60 * 1000
    return 5 * 60 * 1000


def _build_order_flow_coverage(
    *,
    oi_rows: list[dict[str, Any]],
    taker_rows: list[dict[str, Any]],
    funding_rows: list[dict[str, Any]],
    kline_first_timestamp: int,
    kline_last_timestamp: int,
    timeframe_ms: int,
) -> dict[str, Any]:
    candidates: list[int] = []
    for row in list(oi_rows) + list(taker_rows) + list(funding_rows):
        if not isinstance(row, dict):
            continue
        ts = _to_int(row.get("timestamp"), default=0)
        if ts > 0:
            candidates.append(ts)
    order_first = min(candidates) if candidates else 0
    order_last = max(candidates) if candidates else 0
    kline_first = _to_int(kline_first_timestamp, default=0)
    kline_last = _to_int(kline_last_timestamp, default=0)
    missing_before = max(0, order_first - kline_first) if (order_first > 0 and kline_first > 0) else 0
    missing_after = max(0, kline_last - order_last) if (order_last > 0 and kline_last > 0) else 0

    if order_first <= 0 or order_last <= 0:
        status = "insufficient"
    elif missing_before <= max(0, timeframe_ms) and missing_after <= max(0, timeframe_ms):
        status = "ok"
    elif missing_before > max(0, timeframe_ms) and missing_after > max(0, timeframe_ms):
        status = "insufficient"
    else:
        status = "partial"
    return {
        "kline_first_timestamp": kline_first if kline_first > 0 else None,
        "kline_last_timestamp": kline_last if kline_last > 0 else None,
        "order_flow_first_timestamp": order_first if order_first > 0 else None,
        "order_flow_last_timestamp": order_last if order_last > 0 else None,
        "coverage_status": status,
        "coverage_missing_before_ms": int(missing_before),
        "coverage_missing_after_ms": int(missing_after),
    }
