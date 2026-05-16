from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def _normalize_http_status(value: Any) -> Optional[int]:
    if value in ("", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_int_or_none(value: Any) -> Optional[int]:
    if value in ("", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def classify_account_error(
    *,
    market_type: str = "",
    reason: str = "",
    http_status: Any = None,
    binance_code: Any = None,
    binance_msg: str = "",
    response_json: Any = None,
    response_text: str = "",
    details: Optional[dict[str, Any]] = None,
) -> str:
    status_code = _normalize_http_status(http_status)
    code_int = _to_int_or_none(binance_code)
    text = " ".join(
        [
            str(reason or "").lower(),
            str(binance_msg or "").lower(),
            str(response_text or "").lower(),
            str(response_json or "").lower(),
            str(details or {}).lower(),
        ]
    )

    if (
        "unexpected_payload" in text
        or "invalid_account_payload" in text
        or "payload_type" in text
        or "account_unexpected_payload_error" in text
    ):
        return "account_unexpected_payload_error"

    if status_code in {404, 405} or "not found" in text or "unknown route" in text or "endpoint" in text:
        return "account_endpoint_error"

    if (
        status_code == 403
        or "permission" in text
        or "not authorized" in text
        or "ip whitelist" in text
        or "ip address" in text
        or "invalid api-key, ip, or permissions" in text
    ):
        return "account_permission_error"

    if (
        status_code in {400, 401}
        or code_int in {-1022, -2014, -2015}
        or "invalid api-key" in text
        or "api-key format invalid" in text
        or "signature" in text
        or "auth" in text
        or "credential" in text
    ):
        return "account_auth_error"

    if (
        status_code is None
        and (
            "transport" in text
            or "timeout" in text
            or "connection" in text
            or "urlerror" in text
            or "httperror" in text
            or "http_request_failed" in text
            or "request_adapter_exception" in text
            or "temporary dns failure" in text
        )
    ):
        return "account_http_transport_error"

    if (
        response_json in (None, {})
        and str(response_text or "").strip() == ""
        and str(reason or "").strip() in {"", "account_snapshot_unavailable"}
    ):
        return "account_unexpected_payload_error"

    return "futures_account_error" if str(market_type).lower() == "futures" else "spot_account_error"


def classify_testnet_error(
    *,
    code: str = "",
    step: str = "",
    message: str = "",
    details: Optional[dict[str, Any]] = None,
) -> str:
    code_text = str(code or "").strip().lower()
    step_text = str(step or "").strip().lower()
    message_text = str(message or "").strip().lower()
    detail_row = dict(details or {})
    account_snapshot = detail_row.get("account_snapshot")
    if not isinstance(account_snapshot, dict):
        account_snapshot = {}
    http_status = detail_row.get("http_status", account_snapshot.get("http_status"))
    binance_code = detail_row.get("binance_code", account_snapshot.get("binance_code"))
    binance_msg = str(detail_row.get("binance_msg", account_snapshot.get("binance_msg", "")))
    response_json = detail_row.get("response_json", account_snapshot.get("response_json"))
    response_text = str(detail_row.get("response_text", account_snapshot.get("response_text", "")))
    market_type = str(detail_row.get("market_type", account_snapshot.get("market_type", "")))
    text = " ".join(
        [
            code_text,
            step_text,
            message_text,
            str(detail_row).lower(),
        ]
    )
    if code_text in {"environment_not_testnet", "endpoint_mismatch_error"} or (
        step_text == "environment" and "endpoint" in text
    ):
        return "endpoint_mismatch_error"
    if code_text in {"spot_account_error", "futures_account_error"}:
        return code_text
    if code_text in {
        "account_auth_error",
        "account_endpoint_error",
        "account_permission_error",
        "account_http_transport_error",
        "account_unexpected_payload_error",
    }:
        return code_text
    if code_text in {"account_error"} or step_text == "account":
        return classify_account_error(
            market_type=market_type,
            reason=message,
            http_status=http_status,
            binance_code=binance_code,
            binance_msg=binance_msg,
            response_json=response_json,
            response_text=response_text,
            details=detail_row,
        )
    if code_text in {"missing_auth", "missing_auth_material", "missing_api_credentials"}:
        return "missing_auth"
    if code_text in {"signing_error"} or "signature" in text or "signing" in text:
        return "signing_error"
    if code_text in {"auth_error", "unauthorized"} or "auth" in text or "credential" in text:
        return "auth_error"
    if code_text in {"http_transport_error"} or "http_request_failed" in text or "transport_exception" in text:
        return "http_transport_error"
    if code_text in {"time_sync_error"} or step_text == "time":
        return "time_sync_error"
    if "exchange_info" in text:
        return "exchange_info_error"
    if code_text in {"rule_parse_error"} or ("rule" in text and "parse" in text):
        return "rule_parse_error"
    if "rule" in text and ("sync" in text or "symbol" in text):
        return "rule_sync_error"
    if "normalization" in text or "order_param_invalid" in text:
        return "normalization_error"
    if (
        code_text in {"unexpected_payload_error"}
        or "invalid_payload" in code_text
        or "unexpected payload" in text
    ):
        return "unexpected_payload_error"
    if code_text in {"status_error", "status_query_error"} or "status_query" in text:
        return "status_query_error"
    if "submit" in text:
        return "submit_error"
    if "cancel" in text:
        return "cancel_error"
    if "duplicate" in text and ("update" in text or "fill" in text):
        return "duplicate_update_error"
    if "invalid_payload" in text:
        return "unexpected_payload_error"
    if "update" in text or "fill" in text:
        return "update_processing_error"
    if "unsupported" in text or "environment_not_testnet" in text or "mode" in text:
        return "unsupported_mode_error"
    if "connect" in text or "ping" in text or "time" in text or "account" in text:
        return "connectivity_error"
    return "unknown_error"


def classify_runtime_error(
    *,
    code: str = "",
    step: str = "",
    message: str = "",
    details: Optional[dict[str, Any]] = None,
) -> str:
    return classify_testnet_error(code=code, step=step, message=message, details=details)


def summarize_failures_by_category(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for row in list(snapshots or []):
        if not isinstance(row, dict):
            continue
        category = str(row.get("category", "unknown_error")).strip() or "unknown_error"
        counts[category] = counts.get(category, 0) + 1
    return {
        "total": sum(counts.values()),
        "categories": counts,
    }


class FailureSnapshotCatalog:
    def __init__(self, *, max_snapshots: int = 2000):
        self.max_snapshots = max(100, int(max_snapshots))
        self._snapshots: list[dict[str, Any]] = []
        self._sequence = 0

    def append_failure_snapshot(
        self,
        *,
        category: str = "",
        environment: str = "",
        step: str = "",
        message: str = "",
        details: Optional[dict[str, Any]] = None,
        related_order_id: Any = None,
        run_id: str = "",
        timestamp: Optional[Any] = None,
    ) -> dict[str, Any]:
        resolved_details = dict(details or {})
        resolved_category = str(category or "").strip() or classify_runtime_error(
            code=str(resolved_details.get("code", "")),
            step=step,
            message=message,
            details=resolved_details,
        )
        self._sequence += 1
        snapshot = {
            "failure_id": f"FAIL-{self._sequence}",
            "category": resolved_category,
            "timestamp": _normalize_timestamp(timestamp),
            "environment": str(environment or ""),
            "step": str(step or ""),
            "message": str(message or ""),
            "details": resolved_details,
            "related_order_id": str(related_order_id or ""),
            "run_id": str(run_id or ""),
        }
        self._snapshots.append(snapshot)
        if len(self._snapshots) > self.max_snapshots:
            self._snapshots = self._snapshots[-self.max_snapshots :]
        return dict(snapshot)

    def list_failure_snapshots(
        self,
        *,
        category: Optional[str] = None,
        run_id: Optional[str] = None,
        latest: bool = False,
    ) -> list[dict[str, Any]]:
        rows = [dict(item) for item in self._snapshots]
        if category not in (None, ""):
            category_key = str(category)
            rows = [item for item in rows if str(item.get("category", "")) == category_key]
        if run_id not in (None, ""):
            run_key = str(run_id)
            rows = [item for item in rows if str(item.get("run_id", "")) == run_key]
        if latest:
            return [rows[-1]] if rows else []
        return rows


def _normalize_timestamp(value: Optional[Any]) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if value not in (None, ""):
        return str(value)
    return datetime.now(timezone.utc).isoformat()
