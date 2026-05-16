from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from core.binance_endpoints import (
    resolve_account_route,
    resolve_binance_base_url,
    resolve_binance_market_type,
)
from core.error_catalog import classify_account_error
from core.time_sync import is_timestamp_ahead_error


def _normalize_http_status(value: Any) -> Optional[int]:
    if value in ("", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _classify_account_failure_category(
    *,
    market_type: str,
    reason: str,
    http_status: Any = None,
    binance_code: Any = None,
    binance_msg: str = "",
    response_json: Any = None,
    response_text: str = "",
    details: Optional[dict[str, Any]] = None,
) -> str:
    if is_timestamp_ahead_error(
        binance_code=binance_code,
        message=" ".join(
            [
                str(reason or ""),
                str(binance_msg or ""),
                str(response_text or ""),
            ]
        ),
    ):
        return "time_sync_error"
    return classify_account_error(
        market_type=market_type,
        reason=reason,
        http_status=http_status,
        binance_code=binance_code,
        binance_msg=binance_msg,
        response_json=response_json,
        response_text=response_text,
        details=details,
    )


def build_connectivity_result(
    *,
    success: bool,
    mode: str,
    environment: str,
    checked_items: dict[str, Any],
    warnings: list[str] | None = None,
    error: str = "",
) -> dict[str, Any]:
    return {
        "success": bool(success),
        "mode": str(mode),
        "environment": str(environment),
        "checked_items": dict(checked_items),
        "warnings": list(warnings or []),
        "error": str(error or ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def probe_connector_connectivity(
    *,
    connector: Any,
    mode: str,
    environment: str,
) -> dict[str, Any]:
    if connector is None:
        return build_connectivity_result(
            success=False,
            mode=mode,
            environment=environment,
            checked_items={"connector_injected": False},
            warnings=[],
            error="connector_not_available",
        )

    if hasattr(connector, "check_connector_connectivity"):
        result = connector.check_connector_connectivity()
        if isinstance(result, dict):
            return result

    if hasattr(connector, "ping_broker"):
        ping_result = connector.ping_broker()
        if isinstance(ping_result, dict):
            success = bool(ping_result.get("success", ping_result.get("ok", False)))
            return build_connectivity_result(
                success=success,
                mode=mode,
                environment=environment,
                checked_items={"ping_called": True},
                warnings=[],
                error="" if success else str(ping_result.get("error", ping_result.get("reason", "ping_failed"))),
            )

    return build_connectivity_result(
        success=False,
        mode=mode,
        environment=environment,
        checked_items={"connectivity_probe_supported": False},
        warnings=[],
        error="connectivity_check_not_supported",
    )


def run_testnet_connectivity_probe(
    *,
    connector: Any,
    mode: str,
    environment: str,
    market_type: str = "",
    symbols: Optional[list[str]] = None,
) -> dict[str, Any]:
    env = str(environment or "").strip().lower()
    requested_market_type = str(market_type or "").strip().lower()
    resolved_market_type = resolve_binance_market_type(requested_market_type or "spot")
    if requested_market_type == "" and connector is not None and hasattr(connector, "get_market_type"):
        try:
            resolved_market_type = resolve_binance_market_type(str(connector.get_market_type() or "spot"))
        except Exception:
            resolved_market_type = resolve_binance_market_type(requested_market_type or "spot")
    warnings: list[str] = []
    blocking_issues: list[dict[str, str]] = []
    raw_failures: list[dict[str, Any]] = []
    endpoint = resolve_binance_base_url(env if env else "testnet", market_type=resolved_market_type)
    account_route = resolve_account_route(environment=env if env else "testnet", market_type=resolved_market_type)
    account_path = str(account_route.get("resolved_account_path", ""))
    account_base_url = str(account_route.get("resolved_base_url", endpoint))
    time_sync_ok = False
    server_time_offset_ms = 0
    timestamp_source = "local_fallback"

    def fail(
        *,
        code: str,
        step: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
        blocking: bool = True,
        category: str = "",
    ) -> None:
        resolved_category = str(category or code or "unknown_error")
        issue = {"code": str(code), "message": str(message), "category": resolved_category, "step": str(step)}
        if blocking:
            blocking_issues.append(issue)
        raw_failures.append(
            {
                "code": str(code),
                "category": resolved_category,
                "step": str(step),
                "message": str(message),
                "details": dict(details or {}),
            }
        )

    if connector is None:
        fail(code="connector_not_available", step="connector", message="Connector is not available.")
        return _build_testnet_probe_result(
            ok=False,
            mode=mode,
            environment=env or "unknown",
            endpoint=endpoint,
            market_type=resolved_market_type,
            account_path=account_path,
            base_url=account_base_url,
            account_category="",
            auth_ok=False,
            ping_ok=False,
            time_ok=False,
            account_ok=False,
            exchange_info_ok=False,
            account_http_status=None,
            account_binance_code=None,
            account_binance_msg="",
            time_sync_ok=time_sync_ok,
            server_time_offset_ms=server_time_offset_ms,
            timestamp_source=timestamp_source,
            warnings=warnings,
            blocking_issues=blocking_issues,
            raw_failures=raw_failures,
        )

    if env not in {"testnet", "sandbox"}:
        fail(
            code="endpoint_mismatch_error",
            step="environment",
            message=f"Testnet probe requires testnet/sandbox environment, got {env or 'unknown'}.",
            details={"environment": env or "unknown"},
        )
        return _build_testnet_probe_result(
            ok=False,
            mode=mode,
            environment=env or "unknown",
            endpoint=endpoint,
            market_type=resolved_market_type,
            account_path=account_path,
            base_url=account_base_url,
            account_category="",
            auth_ok=False,
            ping_ok=False,
            time_ok=False,
            account_ok=False,
            exchange_info_ok=False,
            account_http_status=None,
            account_binance_code=None,
            account_binance_msg="",
            time_sync_ok=time_sync_ok,
            server_time_offset_ms=server_time_offset_ms,
            timestamp_source=timestamp_source,
            warnings=warnings,
            blocking_issues=blocking_issues,
            raw_failures=raw_failures,
        )

    auth_ok = True
    ping_ok = False
    time_ok = False
    account_ok = False
    exchange_info_ok = False
    account_http_status: Optional[int] = None
    account_binance_code: Any = None
    account_binance_msg = ""

    # Probe signing/auth readiness where available.
    account_request: dict[str, Any] | None = None
    if hasattr(connector, "build_account_request"):
        try:
            candidate = connector.build_account_request()
            account_request = candidate if isinstance(candidate, dict) else None
        except Exception as exc:  # pragma: no cover - defensive path
            account_request = {"ok": False, "error": f"account_request_build_failed:{exc.__class__.__name__}"}

        if not isinstance(account_request, dict) or not bool(account_request.get("ok", False)):
            auth_ok = False
            reason = "missing_api_credentials"
            if isinstance(account_request, dict):
                reason = str(account_request.get("error", reason))
            reason_lower = reason.lower()
            if "missing_api" in reason_lower or "missing_auth" in reason_lower or "credential" in reason_lower:
                category_code = "missing_auth"
            elif "sign" in reason_lower:
                category_code = "signing_error"
            elif "auth" in reason_lower:
                category_code = "auth_error"
            else:
                category_code = "signing_error"
            fail(
                code=category_code,
                step="auth",
                message=f"Account signed request is unavailable: {reason}.",
                details={
                    "account_request": dict(account_request or {}),
                    "market_type": resolved_market_type,
                    "account_path": account_path,
                    "base_url": str(account_route.get("resolved_base_url", endpoint)),
                    "http_status": None,
                },
                category=category_code,
            )
        else:
            account_url = str(account_request.get("url", "")).strip()
            if account_url:
                endpoint = account_url.split("?", 1)[0].replace(str(account_request.get("path", "")), "")
            account_path = str(account_request.get("path", account_path))
    else:
        auth_ok = True

    # Ping probe.
    ping_request = None
    if hasattr(connector, "build_ping_request") and hasattr(connector, "send_binance_request"):
        try:
            ping_request = connector.build_ping_request()
            ping_response = connector.send_binance_request(ping_request)
            ping_ok = bool(isinstance(ping_response, dict) and ping_response.get("ok", True))
            if not ping_ok:
                error_text = str((ping_response or {}).get("error", "ping_failed"))
                code = "http_transport_error" if ("http_" in error_text or "transport_" in error_text) else "connectivity_error"
                fail(
                    code=code,
                    step="ping",
                    message=f"Ping failed: {error_text}.",
                    details={"response": dict(ping_response or {})},
                    category=code,
                )
        except Exception as exc:  # pragma: no cover - defensive path
            ping_ok = False
            fail(
                code="http_transport_error",
                step="ping",
                message=f"Ping probe failed: {exc.__class__.__name__}.",
                category="http_transport_error",
            )
    else:
        fallback = probe_connector_connectivity(connector=connector, mode=mode, environment=env)
        ping_ok = bool(fallback.get("success", False))
        if not ping_ok:
            fail(
                code="connectivity_error",
                step="ping",
                message=f"Connectivity probe failed: {fallback.get('error', 'connectivity_failed')}.",
                details={"connectivity": dict(fallback)},
                category="connectivity_error",
            )

    # Time probe.
    if hasattr(connector, "sync_server_time"):
        try:
            sync_result = connector.sync_server_time()
            if isinstance(sync_result, dict):
                time_sync_ok = bool(sync_result.get("time_sync_ok", False))
                try:
                    server_time_offset_ms = int(sync_result.get("server_time_offset_ms", 0) or 0)
                except (TypeError, ValueError):
                    server_time_offset_ms = 0
                timestamp_source = str(sync_result.get("timestamp_source", "local_fallback") or "local_fallback")
                sync_warning = str(sync_result.get("warning", ""))
                if sync_warning:
                    warnings.append(sync_warning)
        except Exception as exc:  # pragma: no cover - defensive path
            time_sync_ok = False
            server_time_offset_ms = 0
            timestamp_source = "local_fallback"
            warnings.append(f"server_time_sync_failed:{exc.__class__.__name__}")

    if hasattr(connector, "build_time_request") and hasattr(connector, "send_binance_request"):
        try:
            time_request = connector.build_time_request()
            time_response = connector.send_binance_request(time_request)
            time_ok = bool(isinstance(time_response, dict) and time_response.get("ok", True))
            if not time_ok:
                fail(
                    code="time_sync_error",
                    step="time",
                    message=f"Time probe failed: {str((time_response or {}).get('error', 'time_failed'))}.",
                    details={"response": dict(time_response or {})},
                    category="time_sync_error",
                )
        except Exception as exc:  # pragma: no cover - defensive path
            time_ok = False
            fail(
                code="time_sync_error",
                step="time",
                message=f"Time probe failed: {exc.__class__.__name__}.",
                category="time_sync_error",
            )
    else:
        time_ok = ping_ok
    if hasattr(connector, "get_time_sync_status"):
        try:
            time_sync_status = connector.get_time_sync_status()
            if isinstance(time_sync_status, dict):
                time_sync_ok = bool(time_sync_status.get("time_sync_ok", time_sync_ok))
                try:
                    server_time_offset_ms = int(
                        time_sync_status.get("server_time_offset_ms", server_time_offset_ms) or 0
                    )
                except (TypeError, ValueError):
                    pass
                timestamp_source = str(time_sync_status.get("timestamp_source", timestamp_source) or timestamp_source)
                status_warning = str(time_sync_status.get("warning", ""))
                if status_warning:
                    warnings.append(status_warning)
        except Exception as exc:  # pragma: no cover - defensive path
            warnings.append(f"time_sync_status_unavailable:{exc.__class__.__name__}")

    # Account snapshot probe.
    if hasattr(connector, "get_account_snapshot"):
        try:
            account_snapshot = connector.get_account_snapshot()
            if isinstance(account_snapshot, dict):
                if account_snapshot.get("success") is False:
                    account_ok = False
                    reason_text = str(
                        account_snapshot.get("reason", account_snapshot.get("raw_error", "account_snapshot_failed"))
                    )
                    account_path = str(account_snapshot.get("account_path", account_path))
                    account_base_url = str(account_snapshot.get("base_url", account_base_url))
                    http_status = account_snapshot.get("http_status")
                    response_json = account_snapshot.get("response_json")
                    response_text = str(account_snapshot.get("response_text", ""))
                    binance_code = account_snapshot.get("binance_code")
                    binance_msg = str(account_snapshot.get("binance_msg", ""))
                    account_http_status = _normalize_http_status(http_status)
                    account_binance_code = binance_code
                    account_binance_msg = binance_msg
                    code = _classify_account_failure_category(
                        market_type=resolved_market_type,
                        reason=reason_text,
                        http_status=http_status,
                        binance_code=binance_code,
                        binance_msg=binance_msg,
                        response_json=response_json,
                        response_text=response_text,
                        details=account_snapshot,
                    )
                    fail(
                        code=code,
                        step="account",
                        message=f"Account snapshot failed: {reason_text}.",
                        details={
                            "account_snapshot": dict(account_snapshot),
                            "market_type": str(account_snapshot.get("market_type", resolved_market_type)),
                            "account_path": str(account_snapshot.get("account_path", account_path)),
                            "base_url": str(account_snapshot.get("base_url", account_base_url)),
                            "http_status": http_status,
                            "response_text": response_text,
                            "response_json": response_json,
                            "binance_code": binance_code,
                            "binance_msg": binance_msg,
                            "category": code,
                        },
                        category=code,
                    )
                else:
                    account_ok = True
            else:
                account_ok = False
                code = _classify_account_failure_category(
                    market_type=resolved_market_type,
                    reason="invalid_account_payload_type",
                    http_status=None,
                    binance_code=None,
                    binance_msg="",
                    response_json=None,
                    response_text="",
                    details={"payload_type": type(account_snapshot).__name__},
                )
                account_http_status = None
                account_binance_code = None
                account_binance_msg = ""
                fail(
                    code=code,
                    step="account",
                    message="Account snapshot returned invalid payload.",
                    details={
                        "payload_type": type(account_snapshot).__name__,
                        "market_type": resolved_market_type,
                        "account_path": account_path,
                        "base_url": account_base_url,
                        "http_status": None,
                        "response_text": "",
                        "response_json": None,
                        "binance_code": None,
                        "binance_msg": "",
                        "category": code,
                    },
                    category=code,
                )
        except Exception as exc:  # pragma: no cover - defensive path
            account_ok = False
            reason_text = f"Account snapshot probe failed: {exc.__class__.__name__}."
            code = _classify_account_failure_category(
                market_type=resolved_market_type,
                reason=reason_text,
                http_status=None,
                binance_code=None,
                binance_msg="",
                response_json=None,
                response_text="",
                details={"exception": exc.__class__.__name__},
            )
            account_http_status = None
            account_binance_code = None
            account_binance_msg = ""
            fail(
                code=code,
                step="account",
                message=reason_text,
                details={
                    "market_type": resolved_market_type,
                    "account_path": account_path,
                    "base_url": account_base_url,
                    "http_status": None,
                    "response_text": "",
                    "response_json": None,
                    "binance_code": None,
                    "binance_msg": "",
                    "category": code,
                },
                category=code,
            )
    else:
        account_ok = True

    # Exchange info probe.
    if hasattr(connector, "get_exchange_info"):
        target_symbols = [
            str(item or "").strip().upper()
            for item in list(symbols or [])
            if str(item or "").strip()
        ]
        try:
            exchange_info = connector.get_exchange_info(symbols=target_symbols if target_symbols else None)
            has_symbols = isinstance(exchange_info, dict) and isinstance(exchange_info.get("symbols"), list)
            exchange_info_ok = bool(has_symbols and len(exchange_info.get("symbols", [])) > 0)
            if not exchange_info_ok:
                fail(
                    code="exchange_info_error",
                    step="exchange_info",
                    message="Exchange info probe failed or returned empty symbols.",
                    details={"symbols": target_symbols, "exchange_info": dict(exchange_info or {}) if isinstance(exchange_info, dict) else {}},
                    category="exchange_info_error",
                )
        except Exception as exc:  # pragma: no cover - defensive path
            exchange_info_ok = False
            fail(
                code="exchange_info_error",
                step="exchange_info",
                message=f"Exchange info probe failed: {exc.__class__.__name__}.",
                category="exchange_info_error",
            )
    else:
        exchange_info_ok = True

    ok = (
        auth_ok
        and ping_ok
        and time_ok
        and account_ok
        and exchange_info_ok
        and len(blocking_issues) == 0
    )
    account_category = ""
    for item in raw_failures:
        if not isinstance(item, dict):
            continue
        if str(item.get("step", "")) != "account":
            continue
        account_category = str(item.get("category", item.get("code", "")))
        if account_category:
            break
    return _build_testnet_probe_result(
        ok=ok,
        mode=mode,
        environment=env,
        endpoint=endpoint,
        market_type=resolved_market_type,
        account_path=account_path,
        base_url=account_base_url,
        account_category=account_category,
        auth_ok=auth_ok,
        ping_ok=ping_ok,
        time_ok=time_ok,
        account_ok=account_ok,
        exchange_info_ok=exchange_info_ok,
        account_http_status=account_http_status,
        account_binance_code=account_binance_code,
        account_binance_msg=account_binance_msg,
        time_sync_ok=time_sync_ok,
        server_time_offset_ms=server_time_offset_ms,
        timestamp_source=timestamp_source,
        warnings=warnings,
        blocking_issues=blocking_issues,
        raw_failures=raw_failures,
    )


def _build_testnet_probe_result(
    *,
    ok: bool,
    mode: str,
    environment: str,
    endpoint: str,
    market_type: str,
    account_path: str,
    base_url: str,
    account_category: str,
    auth_ok: bool,
    ping_ok: bool,
    time_ok: bool,
    account_ok: bool,
    exchange_info_ok: bool,
    account_http_status: Optional[int],
    account_binance_code: Any,
    account_binance_msg: str,
    time_sync_ok: bool,
    server_time_offset_ms: int,
    timestamp_source: str,
    warnings: list[str],
    blocking_issues: list[dict[str, str]],
    raw_failures: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "ok": bool(ok),
        "mode": str(mode or ""),
        "environment": str(environment or ""),
        "endpoint": str(endpoint or ""),
        "market_type": str(market_type or "spot"),
        "account_path": str(account_path or ""),
        "base_url": str(base_url or ""),
        "account_category": str(account_category or ""),
        "http_status": account_http_status,
        "binance_code": account_binance_code,
        "binance_msg": str(account_binance_msg or ""),
        "auth_ok": bool(auth_ok),
        "ping_ok": bool(ping_ok),
        "time_ok": bool(time_ok),
        "time_sync_ok": bool(time_sync_ok),
        "server_time_offset_ms": int(server_time_offset_ms),
        "timestamp_source": str(timestamp_source or "local_fallback"),
        "account_ok": bool(account_ok),
        "exchange_info_ok": bool(exchange_info_ok),
        "warnings": list(dict.fromkeys([str(item) for item in warnings if str(item)])),
        "blocking_issues": list(blocking_issues),
        "raw_failures": list(raw_failures),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
