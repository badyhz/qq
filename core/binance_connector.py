from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from core.account_sync import normalize_account_details
from core.binance_endpoints import (
    VALID_MARKET_TYPES,
    resolve_account_route,
    resolve_binance_base_url,
    resolve_binance_market_type,
    resolve_binance_path,
)
from core.binance_exchange_info import parse_binance_exchange_info
from core.binance_http import (
    build_public_request,
    build_signed_request,
    build_urllib_passthrough_transport,
    send_binance_request,
)
from core.connectivity_check import build_connectivity_result, run_testnet_connectivity_probe as probe_testnet_connectivity
from core.error_catalog import classify_account_error
from core.http_error_parser import (
    build_http_error_from_exception,
    build_http_error_from_response,
    extract_binance_code_msg,
)
from core.public_market_data import normalize_binance_klines_payload, normalize_kline_interval
from core.time_sync import (
    compute_server_time_offset_ms,
    local_timestamp_ms,
    parse_server_time_ms,
)


ACTIVE_STATUSES = {"NEW", "ACCEPTED", "PARTIALLY_FILLED"}
VALID_ENVIRONMENTS = {"live", "testnet", "sandbox"}
VALID_MODES = {"live", "dry-run", "testnet", "sandbox"}


class BinanceConnector:
    """Lightweight, mockable Binance connector that conforms to BrokerConnector protocol.

    The connector accepts an optional `request_adapter(action, payload)` callable so tests or
    upper layers can provide transport behavior without coupling execution to any Binance SDK.
    """

    def __init__(
        self,
        *,
        request_adapter: Optional[Callable[[str, dict[str, Any]], Any]] = None,
        transport: Optional[Callable[[dict[str, Any]], Any]] = None,
        enabled: bool = True,
        symbol: str = "",
        mode: str = "live",
        environment: str = "live",
        market_type: str = "spot",
        api_key: str = "",
        api_secret: str = "",
        recv_window: int = 5000,
        symbol_rules: Optional[dict[str, dict[str, Any]]] = None,
    ):
        self.request_adapter = request_adapter
        self.transport = transport
        self.enabled = bool(enabled)
        self.symbol = str(symbol or "").strip().upper()
        self.mode = str(mode or "live").strip().lower()
        self.environment = str(environment or "live").strip().lower()
        self.market_type = resolve_binance_market_type(market_type)
        self.api_key = str(api_key or "").strip()
        raw_api_secret = str(api_secret or "")
        self.api_secret = raw_api_secret.strip()
        self._auth_warnings: list[str] = []
        if raw_api_secret != self.api_secret:
            self._auth_warnings.append("api_secret_trimmed_whitespace")
        self.recv_window = max(1, int(recv_window))
        self.symbol_rules = dict(symbol_rules or {})
        self._order_updates: list[dict[str, Any]] = []
        self._fills: list[dict[str, Any]] = []
        self._order_symbol_by_id: dict[str, str] = {}
        self._default_transport_enabled = False
        self._default_transport_error = ""
        self._server_time_offset_ms = 0
        self._time_sync_ok = False
        self._timestamp_source = "local_fallback"
        self._time_sync_warning = "server_time_not_synced"
        self._last_server_time_ms: Optional[int] = None
        self._last_time_sync_at = ""
        self._ensure_default_transport()

    def _ensure_default_transport(self) -> None:
        if self.mode == "dry-run":
            return
        if callable(self.request_adapter) or callable(self.transport):
            return
        try:
            self.transport = build_urllib_passthrough_transport()
            self._default_transport_enabled = callable(self.transport)
        except Exception as exc:  # pragma: no cover - defensive path
            self.transport = None
            self._default_transport_enabled = False
            self._default_transport_error = f"default_transport_build_failed:{exc.__class__.__name__}"

    def _auth_material_present(self) -> bool:
        return self.api_key != "" and self.api_secret != ""

    def is_enabled(self) -> bool:
        if self.mode == "dry-run":
            return True
        env_check = self.validate_binance_environment()
        if not env_check.get("success", False):
            return False
        if not self.enabled:
            return False
        if callable(self.request_adapter):
            return True
        if not callable(self.transport):
            return False
        return self._auth_material_present()

    def get_unavailability_reason(self) -> str:
        env_check = self.validate_binance_environment()
        if not env_check.get("success", False):
            return str(env_check.get("error", "binance_environment_invalid"))
        if self.mode == "dry-run":
            return ""
        if not self.enabled:
            return "binance_connector_disabled"
        if callable(self.request_adapter):
            return ""
        if not callable(self.transport):
            return self._default_transport_error or "default_transport_unavailable"
        if not self._auth_material_present():
            return "missing_auth_material"
        return ""

    def get_environment(self) -> dict[str, str]:
        return {
            "mode": self.mode,
            "environment": self.environment,
            "market_type": self.market_type,
        }

    def get_market_type(self) -> str:
        return self.market_type

    def resolve_account_route(self) -> dict[str, str]:
        route = resolve_account_route(environment=self.environment, market_type=self.market_type)
        return {
            "market_type": self.market_type,
            "resolved_account_path": str(route.get("resolved_account_path", "")),
            "resolved_base_url": str(route.get("resolved_base_url", "")),
            "url": str(route.get("url", "")),
        }

    def validate_binance_environment(self) -> dict[str, Any]:
        warnings: list[str] = list(self._auth_warnings)
        has_request_adapter = callable(self.request_adapter)
        has_transport = callable(self.transport)
        auth_material_present = self._auth_material_present()
        transport_ready = bool(has_request_adapter or has_transport)
        checked_items = {
            "mode_valid": self.mode in VALID_MODES,
            "environment_valid": self.environment in VALID_ENVIRONMENTS,
            "market_type_valid": self.market_type in VALID_MARKET_TYPES,
            "enabled": bool(self.enabled),
            "has_request_adapter": has_request_adapter,
            "has_transport": has_transport,
            "transport_ready": transport_ready,
            "auth_material_present": auth_material_present,
            "has_api_key": self.api_key != "",
            "has_api_secret": self.api_secret != "",
            "auth_warnings": list(self._auth_warnings),
            "using_default_transport": bool(self._default_transport_enabled),
            "default_transport_error": str(self._default_transport_error or ""),
            "market_type": self.market_type,
            "base_url": resolve_binance_base_url(
                self.environment,
                market_type=self.market_type,
            ),
        }
        if self.environment not in VALID_ENVIRONMENTS:
            return build_connectivity_result(
                success=False,
                mode=self.mode,
                environment=self.environment,
                checked_items=checked_items,
                warnings=warnings,
                error="invalid_binance_environment",
            )
        if self.mode not in VALID_MODES:
            return build_connectivity_result(
                success=False,
                mode=self.mode,
                environment=self.environment,
                checked_items=checked_items,
                warnings=warnings,
                error="invalid_connector_mode",
            )
        if self.market_type not in VALID_MARKET_TYPES:
            return build_connectivity_result(
                success=False,
                mode=self.mode,
                environment=self.environment,
                checked_items=checked_items,
                warnings=warnings,
                error="invalid_market_type",
            )
        if self.mode == "dry-run":
            warnings.append("connector_running_in_dry_run_mode")
            return build_connectivity_result(
                success=True,
                mode=self.mode,
                environment=self.environment,
                checked_items=checked_items,
                warnings=warnings,
                error="",
            )
        if not transport_ready:
            return build_connectivity_result(
                success=False,
                mode=self.mode,
                environment=self.environment,
                checked_items=checked_items,
                warnings=warnings,
                error=self._default_transport_error or "default_transport_unavailable",
            )
        if not auth_material_present and not has_request_adapter:
            return build_connectivity_result(
                success=False,
                mode=self.mode,
                environment=self.environment,
                checked_items=checked_items,
                warnings=warnings,
                error="missing_auth_material",
            )
        return build_connectivity_result(
            success=True,
            mode=self.mode,
            environment=self.environment,
            checked_items=checked_items,
            warnings=warnings,
            error="",
        )

    def check_connector_connectivity(self) -> dict[str, Any]:
        env_check = self.validate_binance_environment()
        has_request_adapter = callable(self.request_adapter)
        has_transport = callable(self.transport)
        transport_ready = bool(has_request_adapter or has_transport)
        auth_material_present = self._auth_material_present()
        account_route = self.resolve_account_route()
        if not env_check.get("success", False):
            checked_items = dict(env_check.get("checked_items", {}))
            checked_items.update(
                {
                    "has_request_adapter": has_request_adapter,
                    "has_transport": has_transport,
                    "transport_ready": transport_ready,
                    "auth_material_present": auth_material_present,
                    "market_type": self.market_type,
                    "resolved_account_path": str(account_route.get("resolved_account_path", "")),
                    "resolved_base_url": str(account_route.get("resolved_base_url", "")),
                }
            )
            env_check["checked_items"] = checked_items
            return env_check
        if self.mode == "dry-run":
            return env_check
        if not self.enabled:
            return build_connectivity_result(
                success=False,
                mode=self.mode,
                environment=self.environment,
                checked_items={
                    "enabled": False,
                    "market_type": self.market_type,
                    "has_request_adapter": has_request_adapter,
                    "has_transport": has_transport,
                    "transport_ready": transport_ready,
                    "auth_material_present": auth_material_present,
                    "resolved_account_path": str(account_route.get("resolved_account_path", "")),
                    "resolved_base_url": str(account_route.get("resolved_base_url", "")),
                },
                warnings=[],
                error="binance_connector_disabled",
            )
        if not transport_ready:
            return build_connectivity_result(
                success=False,
                mode=self.mode,
                environment=self.environment,
                checked_items={
                    "market_type": self.market_type,
                    "has_request_adapter": has_request_adapter,
                    "has_transport": has_transport,
                    "transport_ready": transport_ready,
                    "auth_material_present": auth_material_present,
                    "resolved_account_path": str(account_route.get("resolved_account_path", "")),
                    "resolved_base_url": str(account_route.get("resolved_base_url", "")),
                },
                warnings=[],
                error=self._default_transport_error or "default_transport_unavailable",
            )
        if not auth_material_present and not has_request_adapter:
            return build_connectivity_result(
                success=False,
                mode=self.mode,
                environment=self.environment,
                checked_items={
                    "market_type": self.market_type,
                    "has_request_adapter": has_request_adapter,
                    "has_transport": has_transport,
                    "transport_ready": transport_ready,
                    "auth_material_present": auth_material_present,
                    "resolved_account_path": str(account_route.get("resolved_account_path", "")),
                    "resolved_base_url": str(account_route.get("resolved_base_url", "")),
                },
                warnings=[],
                error="missing_auth_material",
            )
        try:
            ping_request = self.build_ping_request()
            ping_result = self.send_binance_request(ping_request)
            time_request = self.build_time_request()
            account_request = self.build_account_request()
        except Exception as exc:
            return build_connectivity_result(
                success=False,
                mode=self.mode,
                environment=self.environment,
                checked_items={
                    "ping_called": True,
                    "market_type": self.market_type,
                    "has_request_adapter": has_request_adapter,
                    "has_transport": has_transport,
                    "transport_ready": transport_ready,
                    "auth_material_present": auth_material_present,
                    "resolved_account_path": str(account_route.get("resolved_account_path", "")),
                    "resolved_base_url": str(account_route.get("resolved_base_url", "")),
                },
                warnings=[],
                error=f"connectivity_check_failed:{exc.__class__.__name__}",
            )
        checked_items = {
            "has_request_adapter": has_request_adapter,
            "has_transport": has_transport,
            "transport_ready": transport_ready,
            "auth_material_present": auth_material_present,
            "market_type": self.market_type,
            "ping_called": True,
            "ping_result_present": ping_result is not None,
            "time_request_built": bool(time_request.get("ok", False)),
            "account_request_built": bool(account_request.get("ok", False)),
            "base_url": resolve_binance_base_url(
                self.environment,
                market_type=self.market_type,
            ),
            "resolved_account_path": str(account_route.get("resolved_account_path", "")),
            "resolved_base_url": str(account_route.get("resolved_base_url", "")),
        }
        if isinstance(ping_result, dict) and ping_result.get("ok") is False:
            return build_connectivity_result(
                success=False,
                mode=self.mode,
                environment=self.environment,
                checked_items=checked_items,
                warnings=[],
                error=str(ping_result.get("error", ping_result.get("reason", "ping_failed"))),
            )
        warnings: list[str] = []
        if isinstance(account_request, dict) and not account_request.get("ok", True):
            warnings.append(str(account_request.get("error", "account_request_unavailable")))
        return build_connectivity_result(
            success=True,
            mode=self.mode,
            environment=self.environment,
            checked_items=checked_items,
            warnings=warnings,
            error="",
        )

    def ping_broker(self) -> dict[str, Any]:
        return self.check_connector_connectivity()

    def run_testnet_connectivity_probe(self, symbols: Optional[list[str]] = None) -> dict[str, Any]:
        return probe_testnet_connectivity(
            connector=self,
            mode=self.mode,
            environment=self.environment,
            market_type=self.market_type,
            symbols=symbols,
        )

    def build_ping_request(self) -> dict[str, Any]:
        path = resolve_binance_path("ping", market_type=self.market_type)
        return build_public_request(
            method="GET",
            path=path,
            environment=self.environment,
            market_type=self.market_type,
            params={},
        )

    def build_time_request(self) -> dict[str, Any]:
        path = resolve_binance_path("time", market_type=self.market_type)
        return build_public_request(
            method="GET",
            path=path,
            environment=self.environment,
            market_type=self.market_type,
            params={},
        )

    def sync_server_time(self) -> dict[str, Any]:
        warning = ""
        request_payload = self.build_time_request()
        response = self.send_binance_request(request_payload)
        server_time_ms = None
        local_time_ms = local_timestamp_ms()
        http_status = None
        binance_code = None
        binance_msg = ""
        response_text = ""
        if isinstance(response, dict):
            http_status = _extract_http_status(response)
            binance_code = response.get("binance_code")
            binance_msg = str(response.get("binance_msg", ""))
            response_text = str(response.get("response_text", ""))
            payload = response.get("data", response)
            server_time_ms = parse_server_time_ms(payload)
            if server_time_ms is None and response.get("ok", True) and isinstance(payload, dict):
                server_time_ms = parse_server_time_ms(payload.get("data"))
        if isinstance(server_time_ms, int):
            self._server_time_offset_ms = compute_server_time_offset_ms(
                server_time_ms=server_time_ms,
                local_time_ms=local_time_ms,
            )
            self._time_sync_ok = True
            self._timestamp_source = "server_time"
            self._time_sync_warning = ""
            self._last_server_time_ms = int(server_time_ms)
            self._last_time_sync_at = _now_iso()
        else:
            warning = "server_time_unavailable_fallback_local_time"
            self._time_sync_ok = False
            self._timestamp_source = "local_fallback"
            self._time_sync_warning = warning
            self._last_server_time_ms = None
        result = self.get_time_sync_status()
        result.update(
            {
                "success": bool(result.get("time_sync_ok", False)),
                "warning": warning or str(result.get("warning", "")),
                "http_status": http_status,
                "binance_code": binance_code,
                "binance_msg": binance_msg,
                "response_text": response_text,
            }
        )
        return result

    def get_server_time_offset_ms(self) -> int:
        return int(self._server_time_offset_ms)

    def get_time_sync_status(self) -> dict[str, Any]:
        return {
            "time_sync_ok": bool(self._time_sync_ok),
            "server_time_offset_ms": int(self._server_time_offset_ms),
            "timestamp_source": str(self._timestamp_source or "local_fallback"),
            "warning": str(self._time_sync_warning or ""),
            "server_time_ms": self._last_server_time_ms,
            "synced_at": str(self._last_time_sync_at or ""),
        }

    def build_signed_timestamp(self, *, auto_sync: bool = True) -> int:
        if auto_sync and not self._time_sync_ok and self.mode != "dry-run":
            self.sync_server_time()
        current_local_ms = local_timestamp_ms()
        if self._time_sync_ok:
            self._timestamp_source = "server_time"
            return int(current_local_ms + self._server_time_offset_ms)
        self._timestamp_source = "local_fallback"
        if self._time_sync_warning == "":
            self._time_sync_warning = "server_time_unavailable_fallback_local_time"
        return int(current_local_ms)

    def _decorate_signed_request_payload(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request_payload, dict):
            return request_payload
        status = self.get_time_sync_status()
        request_payload["time_sync_ok"] = bool(status.get("time_sync_ok", False))
        request_payload["server_time_offset_ms"] = int(status.get("server_time_offset_ms", 0))
        request_payload["timestamp_source"] = str(status.get("timestamp_source", "local_fallback"))
        warning = str(status.get("warning", ""))
        if warning:
            request_payload["time_sync_warning"] = warning
        return request_payload

    def build_account_request(self) -> dict[str, Any]:
        route = self.resolve_account_route()
        signed_timestamp = self.build_signed_timestamp(auto_sync=False) if self._auth_material_present() else None
        payload = build_signed_request(
            method="GET",
            path=str(route.get("resolved_account_path", "")),
            environment=self.environment,
            market_type=self.market_type,
            api_key=self.api_key,
            api_secret=self.api_secret,
            params={},
            recv_window=self.recv_window,
            timestamp_ms=signed_timestamp,
        )
        payload = self._decorate_signed_request_payload(payload)
        payload["market_type"] = self.market_type
        payload["resolved_account_path"] = str(route.get("resolved_account_path", ""))
        payload["resolved_base_url"] = str(route.get("resolved_base_url", ""))
        return payload

    def send_binance_request(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        if callable(self.request_adapter):
            try:
                adapter_result = self.request_adapter("http_request", dict(request_payload))
            except Exception as exc:
                if not isinstance(exc, TypeError):
                    return build_http_error_from_exception(
                        exc,
                        request_payload=request_payload,
                        error_prefix="request_adapter_exception",
                    )
                # Backward compatibility for adapters expecting non-http-request invocation path.
                # Legacy adapters will continue into transport fallback below.
                pass
            else:
                if isinstance(adapter_result, dict):
                    if adapter_result.get("ok", True) is False:
                        return build_http_error_from_response(
                            adapter_result,
                            request_payload=request_payload,
                            default_error="http_request_failed",
                        )
                    merged = dict(request_payload)
                    merged.update(adapter_result)
                    merged.setdefault("ok", True)
                    return merged
                return {"ok": True, "request": dict(request_payload), "data": adapter_result}
        return send_binance_request(request_payload, transport=self.transport)

    def get_symbol_rules(self, symbol: str) -> dict[str, Any]:
        return dict(self.symbol_rules.get(str(symbol or "").strip().upper(), {}))

    def submit_order(self, request: dict[str, Any]) -> dict[str, Any]:
        if not self.is_enabled():
            return {
                "accepted": False,
                "reason": self.get_unavailability_reason(),
                "status": "REJECTED",
                "order_id": "",
            }
        raw = self._call("submit_order", request)
        normalized = normalize_binance_order(raw, default_request=request)
        if not normalized["accepted"]:
            return normalized
        order_id = str(normalized.get("order_id", "")).strip()
        order_symbol = str(normalized.get("symbol", "")).strip().upper()
        if order_id and order_symbol:
            self._order_symbol_by_id[order_id] = order_symbol
        self._order_updates.append(dict(normalized))
        if _to_float(normalized.get("filled_qty", 0.0)) > 0:
            self._fills.append(
                {
                    "fill_id": _build_fill_id(normalized),
                    "order_id": normalized.get("order_id", ""),
                    "trade_id": normalized.get("trade_id"),
                    "symbol": normalized.get("symbol", ""),
                    "side": normalized.get("side", ""),
                    "qty": normalized.get("qty", 0.0),
                    "filled_qty": normalized.get("filled_qty", 0.0),
                    "remaining_qty": normalized.get("remaining_qty", 0.0),
                    "avg_fill_price": normalized.get("avg_fill_price", 0.0),
                    "status": normalized.get("status", ""),
                    "timestamp": normalized.get("timestamp", _now_iso()),
                }
            )
        return normalized

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        if not self.is_enabled():
            return {"accepted": False, "reason": self.get_unavailability_reason()}
        raw = self._call("cancel_order", {"order_id": str(order_id)})
        normalized = normalize_binance_order(raw, default_request={"order_id": str(order_id)})
        if normalized.get("order_id") in ("", None):
            normalized["order_id"] = str(order_id)
        order_symbol = str(normalized.get("symbol", "")).strip().upper()
        if str(normalized.get("order_id", "")).strip() and order_symbol:
            self._order_symbol_by_id[str(normalized["order_id"]).strip()] = order_symbol
        self._order_updates.append(dict(normalized))
        return normalized

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        if not self.is_enabled():
            return None
        raw = self._call("get_order", {"order_id": str(order_id)})
        raw = _unwrap_response(raw)
        if raw in (None, ""):
            return None
        normalized = normalize_binance_order(raw, default_request={"order_id": str(order_id)})
        order_symbol = str(normalized.get("symbol", "")).strip().upper()
        if str(normalized.get("order_id", "")).strip() and order_symbol:
            self._order_symbol_by_id[str(normalized["order_id"]).strip()] = order_symbol
        return normalized

    def get_open_orders(self) -> list[dict[str, Any]]:
        if not self.is_enabled():
            return []
        raw_orders = self._call("get_open_orders", {})
        raw_orders = _unwrap_response(raw_orders)
        if not isinstance(raw_orders, list):
            return []
        normalized = [normalize_binance_order(raw) for raw in raw_orders]
        return [row for row in normalized if row.get("status") in ACTIVE_STATUSES]

    def get_positions(self) -> list[dict[str, Any]]:
        if not self.is_enabled():
            return []
        raw_positions = self._call("get_positions", {})
        raw_positions = _unwrap_response(raw_positions)
        if not isinstance(raw_positions, list):
            return []
        rows: list[dict[str, Any]] = []
        for raw in raw_positions:
            normalized = normalize_binance_position(raw)
            if normalized:
                rows.append(normalized)
        return rows

    def get_account_snapshot(self) -> dict[str, Any]:
        account_route = self.resolve_account_route()
        if not self.is_enabled():
            reason = self.get_unavailability_reason()
            category = classify_account_error(
                market_type=self.market_type,
                reason=reason,
                http_status=None,
                details={"market_type": self.market_type},
            )
            return {
                "success": False,
                "reason": reason,
                "category": category,
                "market_type": self.market_type,
                "account_path": str(account_route.get("resolved_account_path", "")),
                "base_url": str(account_route.get("resolved_base_url", "")),
                "http_status": None,
                "response_text": "",
                "response_json": None,
                "request_url": str(account_route.get("url", "")),
                "request_path": str(account_route.get("resolved_account_path", "")),
                "method": "GET",
                "headers_summary": {},
                "error_type": "ConnectorUnavailable",
                "binance_code": None,
                "binance_msg": "",
                "equity": 0.0,
                "wallet_balance": 0.0,
                "available_balance": 0.0,
            }
        raw = self._call("get_account_snapshot", {})
        if isinstance(raw, dict) and raw.get("success") is False:
            reason = str(raw.get("reason", raw.get("raw_error", "account_snapshot_unavailable")))
            account_path = str(raw.get("account_path", account_route.get("resolved_account_path", "")))
            request_url = str(raw.get("request_url", raw.get("url", account_route.get("url", ""))))
            request_path = str(raw.get("request_path", raw.get("path", account_path)))
            response_json = raw.get("response_json")
            if not isinstance(response_json, (dict, list)):
                response_json = None
            response_text = str(raw.get("response_text", ""))
            binance_code, binance_msg = _resolve_binance_code_msg(
                declared_code=raw.get("binance_code"),
                declared_msg=raw.get("binance_msg"),
                response_json=response_json,
                response_text=response_text,
            )
            http_status = _extract_http_status(raw)
            category = str(raw.get("category", "")).strip() or classify_account_error(
                market_type=str(raw.get("market_type", self.market_type)),
                reason=reason,
                http_status=http_status,
                binance_code=binance_code,
                binance_msg=binance_msg,
                response_json=response_json,
                response_text=response_text,
                details=raw,
            )
            return {
                "success": False,
                "reason": reason,
                "category": category,
                "market_type": str(raw.get("market_type", self.market_type)),
                "account_path": account_path,
                "base_url": str(raw.get("base_url", account_route.get("resolved_base_url", ""))),
                "http_status": http_status,
                "response_text": response_text,
                "response_json": response_json,
                "request_url": request_url,
                "request_path": request_path,
                "method": str(raw.get("method", "GET")),
                "headers_summary": dict(raw.get("headers_summary", {})) if isinstance(raw.get("headers_summary"), dict) else {},
                "error_type": str(raw.get("error_type", "")),
                "binance_code": binance_code,
                "binance_msg": binance_msg,
                "host": str(raw.get("host", _extract_host(request_url))),
                "raw_error": str(raw.get("raw_error", reason)),
                "equity": 0.0,
                "wallet_balance": 0.0,
                "available_balance": 0.0,
            }
        if isinstance(raw, dict) and raw.get("ok") is False:
            request_payload = raw.get("request")
            if not isinstance(request_payload, dict):
                request_payload = {}
            request_url = str(
                raw.get(
                    "request_url",
                    raw.get("url", request_payload.get("url", "")),
                )
            )
            account_path = str(
                raw.get(
                    "request_path",
                    raw.get(
                        "account_path",
                        raw.get("path", request_payload.get("path", account_route.get("resolved_account_path", ""))),
                    ),
                )
            )
            base_url = str(
                raw.get(
                    "base_url",
                    account_route.get("resolved_base_url", _extract_base_url(request_url, account_path)),
                )
            )
            http_status = _extract_http_status(raw)
            error_text = str(raw.get("error", raw.get("reason", "account_snapshot_unavailable")))
            response_json = raw.get("response_json")
            if not isinstance(response_json, (dict, list)):
                response_json = None
            response_text = str(raw.get("response_text", ""))
            binance_code, binance_msg = _resolve_binance_code_msg(
                declared_code=raw.get("binance_code"),
                declared_msg=raw.get("binance_msg"),
                response_json=response_json,
                response_text=response_text,
            )
            category = str(raw.get("category", "")).strip() or classify_account_error(
                market_type=self.market_type,
                reason=error_text,
                http_status=http_status,
                binance_code=binance_code,
                binance_msg=binance_msg,
                response_json=response_json,
                response_text=response_text,
                details=raw,
            )
            return {
                "success": False,
                "reason": error_text,
                "category": category,
                "market_type": self.market_type,
                "account_path": account_path,
                "base_url": base_url,
                "http_status": http_status,
                "response_text": response_text,
                "response_json": response_json,
                "request_url": request_url,
                "request_path": account_path,
                "method": str(raw.get("method", request_payload.get("method", "GET"))),
                "headers_summary": dict(raw.get("headers_summary", {})) if isinstance(raw.get("headers_summary"), dict) else {},
                "error_type": str(raw.get("error_type", "")),
                "binance_code": binance_code,
                "binance_msg": binance_msg,
                "host": str(raw.get("host", _extract_host(request_url))),
                "raw_error": error_text,
                "equity": 0.0,
                "wallet_balance": 0.0,
                "available_balance": 0.0,
            }
        raw = _unwrap_response(raw)
        if not isinstance(raw, dict):
            return {
                "success": False,
                "reason": "account_unexpected_payload_error",
                "category": "account_unexpected_payload_error",
                "market_type": self.market_type,
                "account_path": str(account_route.get("resolved_account_path", "")),
                "base_url": str(account_route.get("resolved_base_url", "")),
                "http_status": None,
                "response_text": "",
                "response_json": None,
                "request_url": str(account_route.get("url", "")),
                "request_path": str(account_route.get("resolved_account_path", "")),
                "method": "GET",
                "headers_summary": {},
                "error_type": "UnexpectedPayload",
                "binance_code": None,
                "binance_msg": "",
                "host": str(_extract_host(str(account_route.get("url", "")))),
                "raw_error": f"invalid_account_payload_type:{type(raw).__name__}",
                "equity": 0.0,
                "wallet_balance": 0.0,
                "available_balance": 0.0,
            }
        snapshot = normalize_binance_account_snapshot(raw)
        if _looks_like_account_unexpected_payload(raw=raw, snapshot=snapshot):
            reason = "account_unexpected_payload_error"
            category = classify_account_error(
                market_type=self.market_type,
                reason=reason,
                http_status=None,
                response_json=raw,
                response_text="",
                details={"market_type": self.market_type, "payload_type": "dict"},
            )
            return {
                "success": False,
                "reason": reason,
                "category": category,
                "market_type": self.market_type,
                "account_path": str(account_route.get("resolved_account_path", "")),
                "base_url": str(account_route.get("resolved_base_url", "")),
                "http_status": None,
                "response_text": "",
                "response_json": dict(raw),
                "request_url": str(account_route.get("url", "")),
                "request_path": str(account_route.get("resolved_account_path", "")),
                "method": "GET",
                "headers_summary": {},
                "error_type": "UnexpectedPayload",
                "binance_code": None,
                "binance_msg": "",
                "host": str(_extract_host(str(account_route.get("url", "")))),
                "raw_error": "unexpected_account_payload_shape",
                "equity": 0.0,
                "wallet_balance": 0.0,
                "available_balance": 0.0,
            }
        snapshot["market_type"] = self.market_type
        snapshot["account_path"] = str(account_route.get("resolved_account_path", ""))
        snapshot["base_url"] = str(account_route.get("resolved_base_url", ""))
        snapshot["host"] = str(_extract_host(str(account_route.get("url", ""))))
        return snapshot

    def get_account_details(self) -> dict[str, Any]:
        if not self.is_enabled():
            return {"success": False, "reason": self.get_unavailability_reason()}
        raw = self._call("get_account_details", {})
        if isinstance(raw, dict) and raw.get("ok") is False:
            return {"success": False, "reason": str(raw.get("error", "account_details_unavailable"))}
        raw = _unwrap_response(raw)
        normalized = normalize_account_details(raw)
        normalized["success"] = True
        normalized["reason"] = ""
        return normalized

    def get_exchange_info(self, symbols: Optional[list[str]] = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        normalized_symbols = [
            str(symbol or "").strip().upper()
            for symbol in list(symbols or [])
            if str(symbol or "").strip()
        ]
        if normalized_symbols:
            payload["symbols"] = normalized_symbols
        raw = self._call("get_exchange_info", payload)
        raw = _unwrap_response(raw)
        return dict(raw) if isinstance(raw, dict) else {}

    def fetch_public_klines(
        self,
        *,
        symbol: str,
        interval: str,
        limit: int = 200,
        market_type: str = "spot",
    ) -> dict[str, Any]:
        resolved_symbol = str(symbol or "").strip().upper()
        resolved_interval = normalize_kline_interval(interval)
        resolved_limit = max(1, int(limit or 1))
        resolved_market_type = resolve_binance_market_type(market_type or self.market_type)
        payload = {
            "symbol": resolved_symbol,
            "interval": resolved_interval,
            "limit": resolved_limit,
            "market_type": resolved_market_type,
        }
        raw = self._call("get_public_klines", payload)
        if isinstance(raw, dict) and raw.get("ok") is False:
            http_status = _extract_http_status(raw)
            return {
                "success": False,
                "error": str(raw.get("error", raw.get("reason", "public_kline_fetch_failed"))),
                "symbol": resolved_symbol,
                "interval": resolved_interval,
                "limit": resolved_limit,
                "market_type": resolved_market_type,
                "http_status": http_status,
                "response_text": str(raw.get("response_text", "")),
                "response_json": raw.get("response_json") if isinstance(raw.get("response_json"), (dict, list)) else None,
                "request_url": str(raw.get("request_url", raw.get("url", ""))),
                "request_path": str(raw.get("request_path", raw.get("path", "/api/v3/klines"))),
                "binance_code": raw.get("binance_code"),
                "binance_msg": str(raw.get("binance_msg", "")),
                "klines": [],
            }
        payload_data = _unwrap_response(raw)
        adapted = normalize_binance_klines_payload(
            payload=payload_data,
            symbol=resolved_symbol,
            timeframe=resolved_interval,
        )
        if not adapted.get("success", False):
            return {
                "success": False,
                "error": str(adapted.get("error", "invalid_kline_payload")),
                "symbol": resolved_symbol,
                "interval": resolved_interval,
                "limit": resolved_limit,
                "market_type": resolved_market_type,
                "http_status": None,
                "response_text": "",
                "response_json": payload_data if isinstance(payload_data, (dict, list)) else None,
                "request_url": "",
                "request_path": "/api/v3/klines",
                "binance_code": None,
                "binance_msg": "",
                "klines": [],
            }
        return {
            "success": True,
            "error": "",
            "symbol": resolved_symbol,
            "interval": resolved_interval,
            "limit": resolved_limit,
            "market_type": resolved_market_type,
            "klines": list(adapted.get("klines", [])),
        }

    def sync_symbol_rules(self, symbols: Optional[list[str]] = None) -> dict[str, Any]:
        exchange_info = self.get_exchange_info(symbols=symbols)
        parsed = parse_binance_exchange_info(exchange_info, symbols=symbols)
        incoming_rules = dict(parsed.get("rules", {}))
        for symbol, rule in incoming_rules.items():
            normalized_symbol = str(symbol or "").strip().upper()
            if normalized_symbol == "":
                continue
            self.symbol_rules[normalized_symbol] = dict(rule or {})
        return {
            "success": bool(parsed.get("success", False)),
            "rules": dict(self.symbol_rules),
            "synced_rules": incoming_rules,
            "warnings": list(parsed.get("warnings", [])),
            "missing_symbols": list(parsed.get("missing_symbols", [])),
            "found_symbols": list(parsed.get("found_symbols", [])),
        }

    def poll_order_updates(self) -> list[dict[str, Any]]:
        if self.is_enabled():
            pulled = self._call("poll_order_updates", {})
            pulled = _unwrap_response(pulled)
            if isinstance(pulled, list):
                for raw in pulled:
                    self._order_updates.append(normalize_binance_order(raw))
        rows = [dict(row) for row in self._order_updates]
        self._order_updates = []
        return rows

    def poll_fills(self) -> list[dict[str, Any]]:
        if self.is_enabled():
            pulled = self._call("poll_fills", {})
            pulled = _unwrap_response(pulled)
            if isinstance(pulled, list):
                for raw in pulled:
                    self._fills.append(normalize_binance_fill(raw))
        rows = [dict(row) for row in self._fills]
        self._fills = []
        return rows

    def _call(self, action: str, payload: dict[str, Any]) -> Any:
        if callable(self.request_adapter):
            return self.request_adapter(action, payload)

        request_payload: dict[str, Any] | None = None
        if action == "ping":
            request_payload = self.build_ping_request()
        elif action == "time":
            request_payload = self.build_time_request()
        elif action in {"get_account_snapshot", "get_account_details"}:
            if self._auth_material_present() and not self._time_sync_ok and self.mode != "dry-run":
                self.sync_server_time()
            request_payload = self.build_account_request()
        elif action == "get_exchange_info":
            path = resolve_binance_path("exchange_info", market_type=self.market_type)
            query: dict[str, Any] = {}
            symbols = list(payload.get("symbols", [])) if isinstance(payload, dict) else []
            normalized_symbols = [
                str(item or "").strip().upper()
                for item in symbols
                if str(item or "").strip()
            ]
            if len(normalized_symbols) == 1:
                query["symbol"] = normalized_symbols[0]
            elif len(normalized_symbols) > 1:
                query["symbols"] = json.dumps(normalized_symbols, separators=(",", ":"))
            request_payload = build_public_request(
                method="GET",
                path=path,
                environment=self.environment,
                market_type=self.market_type,
                params=query,
            )
        elif action == "get_public_klines":
            resolved_market_type = resolve_binance_market_type(payload.get("market_type", self.market_type))
            path = "/api/v3/klines" if resolved_market_type == "spot" else "/fapi/v1/klines"
            request_payload = build_public_request(
                method="GET",
                path=path,
                environment=self.environment,
                market_type=resolved_market_type,
                params={
                    "symbol": str(payload.get("symbol", "")).strip().upper(),
                    "interval": normalize_kline_interval(payload.get("interval", "5m")),
                    "limit": max(1, int(payload.get("limit", 200) or 200)),
                },
            )
        elif action == "submit_order":
            symbol = str(payload.get("symbol", self.symbol)).strip().upper()
            side = str(payload.get("side", "")).strip().upper()
            mapped_side = "SELL" if side in {"SHORT", "SELL"} else "BUY"
            qty = max(_to_float(payload.get("qty", payload.get("quantity", 0.0))), 0.0)
            price = max(_to_float(payload.get("price", payload.get("entry_price", 0.0))), 0.0)
            order_type = str(payload.get("type", "LIMIT")).strip().upper() or "LIMIT"
            if price <= 0:
                order_type = "MARKET"
            params = {
                "symbol": symbol,
                "side": mapped_side,
                "type": order_type,
                "quantity": _format_decimal_string(qty),
            }
            if order_type == "LIMIT":
                params["timeInForce"] = "GTC"
                params["price"] = _format_decimal_string(price)
            client_id = str(
                payload.get("client_order_id", payload.get("request_id", payload.get("order_id", "")))
            ).strip()
            if client_id:
                params["newClientOrderId"] = client_id
            request_payload = build_signed_request(
                method="POST",
                path=resolve_binance_path("order", market_type=self.market_type),
                environment=self.environment,
                market_type=self.market_type,
                api_key=self.api_key,
                api_secret=self.api_secret,
                params=params,
                recv_window=self.recv_window,
                timestamp_ms=self.build_signed_timestamp(),
            )
            request_payload = self._decorate_signed_request_payload(request_payload)
        elif action == "cancel_order":
            order_id = str(payload.get("order_id", "")).strip()
            symbol = str(payload.get("symbol", self._order_symbol_by_id.get(order_id, self.symbol))).strip().upper()
            params = {"orderId": order_id}
            if symbol:
                params["symbol"] = symbol
            request_payload = build_signed_request(
                method="DELETE",
                path=resolve_binance_path("order", market_type=self.market_type),
                environment=self.environment,
                market_type=self.market_type,
                api_key=self.api_key,
                api_secret=self.api_secret,
                params=params,
                recv_window=self.recv_window,
                timestamp_ms=self.build_signed_timestamp(),
            )
            request_payload = self._decorate_signed_request_payload(request_payload)
        elif action == "get_order":
            order_id = str(payload.get("order_id", "")).strip()
            symbol = str(payload.get("symbol", self._order_symbol_by_id.get(order_id, self.symbol))).strip().upper()
            params = {"orderId": order_id}
            if symbol:
                params["symbol"] = symbol
            request_payload = build_signed_request(
                method="GET",
                path=resolve_binance_path("order", market_type=self.market_type),
                environment=self.environment,
                market_type=self.market_type,
                api_key=self.api_key,
                api_secret=self.api_secret,
                params=params,
                recv_window=self.recv_window,
                timestamp_ms=self.build_signed_timestamp(),
            )
            request_payload = self._decorate_signed_request_payload(request_payload)
        elif action == "get_open_orders":
            symbol = str(payload.get("symbol", self.symbol)).strip().upper()
            params = {"symbol": symbol} if symbol else {}
            request_payload = build_signed_request(
                method="GET",
                path=resolve_binance_path("open_orders", market_type=self.market_type),
                environment=self.environment,
                market_type=self.market_type,
                api_key=self.api_key,
                api_secret=self.api_secret,
                params=params,
                recv_window=self.recv_window,
                timestamp_ms=self.build_signed_timestamp(),
            )
            request_payload = self._decorate_signed_request_payload(request_payload)
        elif action == "get_positions":
            positions_path = resolve_binance_path("positions", market_type=self.market_type)
            if positions_path == "":
                return []
            request_payload = build_signed_request(
                method="GET",
                path=positions_path,
                environment=self.environment,
                market_type=self.market_type,
                api_key=self.api_key,
                api_secret=self.api_secret,
                params={},
                recv_window=self.recv_window,
                timestamp_ms=self.build_signed_timestamp(),
            )
            request_payload = self._decorate_signed_request_payload(request_payload)
        elif action in {"poll_order_updates", "poll_fills"}:
            return []

        if request_payload is None:
            return None
        response = self.send_binance_request(request_payload)
        return _unwrap_response(response)


def normalize_binance_order(raw: Any, *, default_request: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    row = dict(raw) if isinstance(raw, dict) else {}
    fallback = default_request or {}
    order_id = _pick_str(row, ("orderId", "order_id", "id"), _pick_str(fallback, ("order_id",), ""))
    symbol = _pick_str(row, ("symbol",), _pick_str(fallback, ("symbol",), "")).upper()
    side = _pick_str(row, ("side",), _pick_str(fallback, ("side",), "")).upper()
    status = _normalize_status(_pick_str(row, ("status",), _pick_str(fallback, ("status",), "NEW")))
    qty = _to_float(row.get("origQty", row.get("qty", row.get("quantity", fallback.get("qty", fallback.get("quantity", 0.0))))))
    filled_qty = _to_float(row.get("executedQty", row.get("filled_qty", 0.0)))
    if row.get("remaining_qty") in ("", None):
        remaining_qty = max(qty - filled_qty, 0.0)
    else:
        remaining_qty = _to_float(row.get("remaining_qty", 0.0))
    avg_fill_price = _to_float(row.get("avgPrice", row.get("avg_fill_price", row.get("price", 0.0))))
    request_id = _pick_str(row, ("clientOrderId", "client_order_id", "request_id"), _pick_str(fallback, ("request_id", "client_order_id"), ""))
    accepted = status != "REJECTED"
    if order_id == "":
        accepted = False
    reason = _pick_str(row, ("reason", "msg", "error"), "")
    if not accepted and reason == "":
        reason = "binance_order_rejected"
    return {
        "accepted": accepted,
        "order_id": order_id,
        "client_order_id": request_id,
        "request_id": request_id,
        "trade_id": row.get("trade_id", fallback.get("trade_id")),
        "symbol": symbol,
        "side": side,
        "type": _pick_str(row, ("type", "orderType"), _pick_str(fallback, ("type",), "")),
        "status": status,
        "qty": qty,
        "filled_qty": min(max(filled_qty, 0.0), max(qty, 0.0)) if qty > 0 else max(filled_qty, 0.0),
        "remaining_qty": max(remaining_qty, 0.0),
        "avg_fill_price": avg_fill_price,
        "reason": reason,
        "timestamp": _normalize_timestamp(row.get("updateTime", row.get("time", row.get("timestamp")))),
    }


def normalize_binance_position(raw: Any) -> dict[str, Any]:
    row = dict(raw) if isinstance(raw, dict) else {}
    symbol = _pick_str(row, ("symbol",), "").upper()
    position_amt = _to_float(row.get("positionAmt", row.get("position_amt", row.get("qty", 0.0))))
    if symbol == "":
        return {}
    side = "FLAT"
    if position_amt > 0:
        side = "LONG"
    elif position_amt < 0:
        side = "SHORT"
    return {
        "symbol": symbol,
        "side": side,
        "position_amt": position_amt,
        "qty": abs(position_amt),
        "entry_price": _to_float(row.get("entryPrice", row.get("entry_price", 0.0))),
        "unrealized_pnl": _to_float(row.get("unRealizedProfit", row.get("unrealized_pnl", 0.0))),
        "leverage": _to_float(row.get("leverage", 0.0)),
        "timestamp": _normalize_timestamp(row.get("updateTime", row.get("timestamp"))),
    }


def normalize_binance_account_snapshot(raw: Any) -> dict[str, Any]:
    row = dict(raw) if isinstance(raw, dict) else {}
    wallet_balance = _to_float(
        row.get("totalWalletBalance", row.get("wallet_balance", row.get("walletBalance", 0.0)))
    )
    available_balance = _to_float(
        row.get("availableBalance", row.get("available_balance", row.get("free", 0.0)))
    )
    balances = row.get("balances")
    if isinstance(balances, list):
        free_total = 0.0
        locked_total = 0.0
        for item in balances:
            if not isinstance(item, dict):
                continue
            free_total += _to_float(item.get("free", 0.0))
            locked_total += _to_float(item.get("locked", 0.0))
        if wallet_balance <= 0:
            wallet_balance = free_total + locked_total
        if available_balance <= 0:
            available_balance = free_total
    equity = _to_float(
        row.get(
            "equity",
            row.get(
                "totalMarginBalance",
                row.get("totalWalletBalance", row.get("wallet_balance", wallet_balance)),
            ),
        )
    )
    if equity <= 0:
        equity = wallet_balance
    return {
        "success": True,
        "equity": equity,
        "wallet_balance": wallet_balance,
        "available_balance": available_balance,
        "total_unrealized_pnl": _to_float(row.get("totalUnrealizedProfit", row.get("total_unrealized_pnl", 0.0))),
        "timestamp": _normalize_timestamp(row.get("updateTime", row.get("timestamp"))),
    }


def normalize_binance_fill(raw: Any) -> dict[str, Any]:
    row = dict(raw) if isinstance(raw, dict) else {}
    qty = _to_float(row.get("qty", row.get("executedQty", row.get("lastFilledQty", 0.0))))
    fill_price = _to_float(row.get("price", row.get("avgPrice", row.get("avg_fill_price", 0.0))))
    return {
        "fill_id": _pick_str(row, ("id", "tradeId", "fill_id"), "") or _build_fill_id(row),
        "order_id": _pick_str(row, ("orderId", "order_id"), ""),
        "trade_id": row.get("trade_id"),
        "symbol": _pick_str(row, ("symbol",), "").upper(),
        "side": _pick_str(row, ("side",), "").upper(),
        "qty": qty,
        "filled_qty": _to_float(row.get("filled_qty", qty)),
        "remaining_qty": _to_float(row.get("remaining_qty", 0.0)),
        "avg_fill_price": fill_price,
        "status": _normalize_status(_pick_str(row, ("status",), "FILLED")),
        "timestamp": _normalize_timestamp(row.get("time", row.get("timestamp"))),
    }


def _resolve_binance_code_msg(
    *,
    declared_code: Any,
    declared_msg: Any,
    response_json: Any,
    response_text: str,
) -> tuple[Any, str]:
    code = declared_code
    msg = str(declared_msg or "")
    if code not in ("", None) and msg != "":
        return code, msg
    inferred_code, inferred_msg = extract_binance_code_msg(
        response_json=response_json,
        response_text=response_text,
    )
    if code in ("", None):
        code = inferred_code
    if msg == "":
        msg = str(inferred_msg or "")
    return code, msg


def _looks_like_account_unexpected_payload(*, raw: dict[str, Any], snapshot: dict[str, Any]) -> bool:
    if not isinstance(raw, dict):
        return True
    if raw == {}:
        return True
    expected_keys = {
        "balances",
        "totalWalletBalance",
        "wallet_balance",
        "walletBalance",
        "availableBalance",
        "available_balance",
        "equity",
        "totalMarginBalance",
    }
    if any(key in raw for key in expected_keys):
        return False
    if _to_float(snapshot.get("equity", 0.0)) > 0:
        return False
    if _to_float(snapshot.get("wallet_balance", 0.0)) > 0:
        return False
    if _to_float(snapshot.get("available_balance", 0.0)) > 0:
        return False
    return True


def _normalize_status(status: str) -> str:
    raw = str(status or "").strip().upper()
    if raw == "":
        return "NEW"
    if raw == "PARTIALLY_FILLED":
        return "PARTIALLY_FILLED"
    if raw in {"NEW", "FILLED", "CANCELED", "REJECTED"}:
        return raw
    if raw in {"EXPIRED", "PENDING_CANCEL"}:
        return "CANCELED"
    return raw


def _to_float(value: Any, default: float = 0.0) -> float:
    if value in ("", None):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_decimal_string(value: Any) -> str:
    number = _to_float(value, default=0.0)
    text = f"{number:.12f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _pick_str(row: dict[str, Any], keys: tuple[str, ...], default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value in ("", None):
            continue
        return str(value)
    return default


def _normalize_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (int, float)):
        if value > 1e12:
            value = value / 1000.0
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    if value not in ("", None):
        return str(value)
    return _now_iso()


def _build_fill_id(row: dict[str, Any]) -> str:
    order_id = _pick_str(row, ("order_id", "orderId"), "")
    ts = _normalize_timestamp(row.get("timestamp", row.get("time")))
    qty = _to_float(row.get("filled_qty", row.get("executedQty", row.get("qty", 0.0))))
    price = _to_float(row.get("avg_fill_price", row.get("avgPrice", row.get("price", 0.0))))
    return f"{order_id}:{qty}:{price}:{ts}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_http_status(payload: dict[str, Any]) -> Any:
    for key in ("http_status", "status_code", "status"):
        value = payload.get(key)
        if value in ("", None):
            continue
        return value
    return None


def _extract_host(url: str) -> str:
    value = str(url or "").strip()
    if value == "":
        return ""
    if "://" in value:
        value = value.split("://", 1)[1]
    return value.split("/", 1)[0]


def _extract_base_url(url: str, path: str) -> str:
    text = str(url or "").strip()
    route_path = str(path or "").strip()
    if text == "":
        return ""
    if route_path and route_path in text:
        return text.split(route_path, 1)[0]
    if "://" in text:
        scheme, remain = text.split("://", 1)
        host = remain.split("/", 1)[0]
        return f"{scheme}://{host}"
    return text


def _unwrap_response(raw: Any) -> Any:
    if isinstance(raw, dict) and "data" in raw and raw.get("ok") is True:
        return raw.get("data")
    return raw
