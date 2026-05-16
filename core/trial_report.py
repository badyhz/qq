from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TrialRunJournal:
    def __init__(self, *, max_results: int = 1000):
        self.max_results = max(100, int(max_results))
        self._results: list[dict[str, Any]] = []
        self._sequence = 0

    def append_trial_run_result(
        self,
        *,
        run_id: str = "",
        session_id: str = "",
        started_at: Optional[Any] = None,
        finished_at: Optional[Any] = None,
        mode: str = "",
        environment: str = "",
        checks_performed: Optional[list[str]] = None,
        orders_submitted: int = 0,
        orders_canceled: int = 0,
        orders_filled: int = 0,
        warnings: Optional[list[Any]] = None,
        blocking_issues: Optional[list[Any]] = None,
        final_status: str = "",
        related_audit_event_ids: Optional[list[Any]] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        self._sequence += 1
        resolved_run_id = str(run_id or f"TRIAL-{self._sequence}")
        result = {
            "run_id": resolved_run_id,
            "session_id": str(session_id or ""),
            "started_at": _normalize_timestamp(started_at),
            "finished_at": _normalize_timestamp(finished_at),
            "mode": str(mode or ""),
            "environment": str(environment or ""),
            "checks_performed": [str(item) for item in (checks_performed or []) if str(item)],
            "orders_submitted": max(0, int(orders_submitted or 0)),
            "orders_canceled": max(0, int(orders_canceled or 0)),
            "orders_filled": max(0, int(orders_filled or 0)),
            "warnings": [str(item) for item in (warnings or []) if str(item)],
            "blocking_issues": _normalize_issues(blocking_issues),
            "final_status": str(final_status or "UNKNOWN").upper(),
            "related_audit_event_ids": [
                str(item) for item in (related_audit_event_ids or []) if str(item)
            ],
            "payload": dict(payload or {}),
        }
        self._results.append(result)
        if len(self._results) > self.max_results:
            self._results = self._results[-self.max_results :]
        return dict(result)

    def list_trial_run_results(self, *, final_status: Optional[str] = None) -> list[dict[str, Any]]:
        rows = [dict(item) for item in self._results]
        if final_status in (None, ""):
            return rows
        status_key = str(final_status).upper()
        return [item for item in rows if str(item.get("final_status", "")).upper() == status_key]

    def build_trial_run_review(
        self,
        *,
        run_id: Optional[str] = None,
        final_status: Optional[str] = None,
    ) -> dict[str, Any]:
        all_results = [dict(item) for item in self._results]
        filtered = self.list_trial_run_results(final_status=final_status)
        selected = None
        if run_id not in (None, ""):
            run_key = str(run_id)
            for item in all_results:
                if str(item.get("run_id", "")) == run_key:
                    selected = dict(item)
                    break
        elif filtered:
            selected = dict(filtered[-1])
        latest = dict(all_results[-1]) if all_results else None
        return {
            "latest": latest,
            "selected": selected,
            "results": filtered,
            "filters": {
                "run_id": str(run_id) if run_id not in (None, "") else "",
                "final_status": str(final_status).upper() if final_status not in (None, "") else "",
            },
            "counts": {
                "total": len(all_results),
                "filtered": len(filtered),
            },
        }


class SignalTrialJournal:
    def __init__(self, *, max_results: int = 1000):
        self.max_results = max(100, int(max_results))
        self._results: list[dict[str, Any]] = []
        self._sequence = 0

    def append_signal_trial(
        self,
        *,
        signal_id: str = "",
        run_id: str = "",
        symbol: str = "",
        side: str = "",
        score: Any = None,
        entry_price: Any = None,
        stop_loss: Any = None,
        take_profit: Any = None,
        order_intent: Optional[dict[str, Any]] = None,
        gate_result: Optional[dict[str, Any]] = None,
        normalization_result: Optional[dict[str, Any]] = None,
        preflight_result: Optional[dict[str, Any]] = None,
        final_status: str = "",
        warnings: Optional[list[Any]] = None,
        blocking_issues: Optional[list[Any]] = None,
        submit_result: Optional[dict[str, Any]] = None,
        status_result: Optional[dict[str, Any]] = None,
        cancel_result: Optional[dict[str, Any]] = None,
        source_signal: Optional[dict[str, Any]] = None,
        recorded_at: Optional[Any] = None,
    ) -> dict[str, Any]:
        self._sequence += 1
        resolved_signal_id = str(signal_id or f"SIG-{self._sequence}")
        resolved_run_id = str(run_id or f"SIGTRIAL-{self._sequence}")
        resolved_status = str(final_status or "UNKNOWN").upper()
        result = {
            "signal_trial_id": f"STRIAL-{self._sequence}",
            "signal_id": resolved_signal_id,
            "run_id": resolved_run_id,
            "recorded_at": _normalize_timestamp(recorded_at),
            "symbol": str(symbol or "").upper(),
            "side": str(side or "").upper(),
            "score": _to_float(score),
            "entry_price": _to_float(entry_price),
            "stop_loss": _to_float(stop_loss),
            "take_profit": _to_float(take_profit),
            "order_intent": dict(order_intent or {}),
            "gate_result": dict(gate_result or {}),
            "normalization_result": dict(normalization_result or {}),
            "preflight_result": dict(preflight_result or {}),
            "submit_result": dict(submit_result or {}),
            "status_result": dict(status_result or {}),
            "cancel_result": dict(cancel_result or {}),
            "source_signal": dict(source_signal or {}),
            "warnings": [str(item) for item in (warnings or []) if str(item)],
            "blocking_issues": _normalize_issues(blocking_issues),
            "final_status": resolved_status,
            "safe_to_live": False,
        }
        self._results.append(result)
        if len(self._results) > self.max_results:
            self._results = self._results[-self.max_results :]
        return dict(result)

    def list_signal_trials(
        self,
        *,
        final_status: Optional[str] = None,
        signal_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        rows = [dict(item) for item in self._results]
        if final_status not in (None, ""):
            status_key = str(final_status).upper()
            rows = [item for item in rows if str(item.get("final_status", "")).upper() == status_key]
        if signal_id not in (None, ""):
            key = str(signal_id)
            rows = [item for item in rows if str(item.get("signal_id", "")) == key]
        return rows

    def build_signal_trial_review(
        self,
        *,
        run_id: Optional[str] = None,
        signal_id: Optional[str] = None,
        final_status: Optional[str] = None,
    ) -> dict[str, Any]:
        all_results = [dict(item) for item in self._results]
        filtered = self.list_signal_trials(final_status=final_status, signal_id=signal_id)
        selected: Optional[dict[str, Any]] = None
        if run_id not in (None, ""):
            run_key = str(run_id)
            for item in all_results:
                if str(item.get("run_id", "")) == run_key:
                    selected = dict(item)
                    break
        elif filtered:
            selected = dict(filtered[-1])
        latest = dict(all_results[-1]) if all_results else None
        if not selected:
            return {
                "latest": latest,
                "selected": None,
                "results": filtered,
                "summary": {
                    "signal_qualified": False,
                    "blocked_by_gate": "",
                    "worth_next_testnet_round": False,
                    "safe_to_live": False,
                    "next_actions": ["rerun_signal_dry_gate"],
                },
                "filters": {
                    "run_id": str(run_id or ""),
                    "signal_id": str(signal_id or ""),
                    "final_status": str(final_status or "").upper(),
                },
                "counts": {"total": len(all_results), "filtered": len(filtered)},
            }

        gate_result = dict(selected.get("gate_result", {}))
        blocking = list(selected.get("blocking_issues", []))
        failed_gates = [
            name
            for name in ("preflight_ok", "risk_ok", "normalization_ok", "trial_gate_ok")
            if name in gate_result and not bool(gate_result.get(name, False))
        ]
        blocked_by_gate = failed_gates[0] if failed_gates else ""
        final_status_key = str(selected.get("final_status", "")).upper()
        signal_qualified = len(failed_gates) == 0 and len(blocking) == 0 and final_status_key in {
            "DRY_GATE_ONLY",
            "TESTNET_SUBMITTED",
            "TESTNET_SUBMIT_SUCCESS",
        }
        worth_next_testnet_round = bool(
            signal_qualified
            or final_status_key in {"DRY_GATE_ONLY", "TESTNET_SUBMITTED", "TESTNET_SUBMIT_SUCCESS"}
        )

        next_actions: list[str] = []
        if "preflight_ok" in failed_gates:
            next_actions.append("rerun_preflight")
        if "risk_ok" in failed_gates:
            next_actions.append("adjust_risk_or_signal_size")
        if "normalization_ok" in failed_gates:
            next_actions.append("adjust_price_qty_for_symbol_rules")
        if "trial_gate_ok" in failed_gates:
            next_actions.append("resolve_trial_gate_blockers")
        if len(blocking) > 0 and "resolve_blocking_issues" not in next_actions:
            next_actions.append("resolve_blocking_issues")
        if signal_qualified and final_status_key == "DRY_GATE_ONLY":
            next_actions.append("consider_testnet_submit_next_round")
        if not next_actions:
            next_actions.append("rerun_signal_dry_gate")

        return {
            "latest": latest,
            "selected": selected,
            "results": filtered,
            "summary": {
                "signal_qualified": bool(signal_qualified),
                "blocked_by_gate": blocked_by_gate,
                "worth_next_testnet_round": bool(worth_next_testnet_round),
                "safe_to_live": False,
                "next_actions": list(dict.fromkeys(next_actions)),
            },
            "filters": {
                "run_id": str(run_id or ""),
                "signal_id": str(signal_id or ""),
                "final_status": str(final_status or "").upper(),
            },
            "counts": {"total": len(all_results), "filtered": len(filtered)},
        }


class ScanReportJournal:
    def __init__(self, *, max_results: int = 1000):
        self.max_results = max(100, int(max_results))
        self._results: list[dict[str, Any]] = []
        self._sequence = 0

    def append_scan_report(
        self,
        *,
        scan_id: str = "",
        generated_at: Optional[Any] = None,
        market_data_source: str = "mock",
        symbols: Optional[list[Any]] = None,
        timeframe: str = "5m",
        limit: int = 0,
        strategy_name: str = "right_breakout_v01",
        params: Optional[dict[str, Any]] = None,
        valid_count: int = 0,
        rejected_count: int = 0,
        candidates: Optional[list[Any]] = None,
        rejected_signals: Optional[list[Any]] = None,
        fetch_ok_symbols: Optional[list[Any]] = None,
        fetch_failed_symbols: Optional[list[Any]] = None,
        fetch_errors: Optional[list[Any]] = None,
        warnings: Optional[list[Any]] = None,
        gate_blocked_reasons: Optional[list[Any]] = None,
    ) -> dict[str, Any]:
        existing_idx = None
        resolved_scan_id = str(scan_id or "").strip()
        if resolved_scan_id:
            for idx, item in enumerate(self._results):
                if str(item.get("scan_id", "")).strip() == resolved_scan_id:
                    existing_idx = idx
                    break
        self._sequence += 1
        if resolved_scan_id == "":
            resolved_scan_id = f"SCAN-{self._sequence}"
        existing = dict(self._results[existing_idx]) if existing_idx is not None else {}
        row = {
            "scan_report_id": str(existing.get("scan_report_id", f"SCANREP-{self._sequence}")),
            "scan_id": resolved_scan_id,
            "generated_at": _normalize_timestamp(
                generated_at if generated_at not in (None, "") else existing.get("generated_at")
            ),
            "market_data_source": str(market_data_source or "mock"),
            "symbols": [str(item or "").strip().upper() for item in list(symbols or []) if str(item or "").strip()],
            "timeframe": str(timeframe or "5m").strip() or "5m",
            "limit": max(0, int(limit or 0)),
            "strategy_name": str(strategy_name or "right_breakout_v01"),
            "params": dict(params or {}),
            "valid_count": max(0, int(valid_count or 0)),
            "rejected_count": max(0, int(rejected_count or 0)),
            "candidates": [dict(item) for item in list(candidates or []) if isinstance(item, dict)],
            "rejected_signals": [dict(item) for item in list(rejected_signals or []) if isinstance(item, dict)],
            "fetch_ok_symbols": [
                str(item or "").strip().upper()
                for item in list(fetch_ok_symbols or [])
                if str(item or "").strip()
            ],
            "fetch_failed_symbols": [
                str(item or "").strip().upper()
                for item in list(fetch_failed_symbols or [])
                if str(item or "").strip()
            ],
            "fetch_errors": [dict(item) for item in list(fetch_errors or []) if isinstance(item, dict)],
            "warnings": [str(item) for item in list(warnings or []) if str(item)],
            "gate_blocked_reasons": [dict(item) for item in list(gate_blocked_reasons or []) if isinstance(item, dict)],
            "safe_to_live": False,
        }
        if existing_idx is not None:
            self._results[existing_idx] = row
        else:
            self._results.append(row)
        if len(self._results) > self.max_results:
            self._results = self._results[-self.max_results :]
        return dict(row)

    def list_scan_reports(
        self,
        *,
        market_data_source: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        rows = [dict(item) for item in self._results]
        if market_data_source not in (None, ""):
            source = str(market_data_source).strip().lower()
            rows = [item for item in rows if str(item.get("market_data_source", "")).strip().lower() == source]
        return rows

    def build_scan_review(self) -> dict[str, Any]:
        rows = [dict(item) for item in self._results]
        latest = dict(rows[-1]) if rows else {}
        reasons_count: dict[str, int] = {}
        for report in rows:
            for item in list(report.get("rejected_signals", [])):
                if not isinstance(item, dict):
                    continue
                reason = str(item.get("reason", "")).strip()
                if reason == "":
                    continue
                reasons_count[reason] = reasons_count.get(reason, 0) + 1
        common_rejections = [
            {"reason": key, "count": value}
            for key, value in sorted(reasons_count.items(), key=lambda row: (-row[1], row[0]))
        ]
        latest_candidates = list(latest.get("candidates", [])) if isinstance(latest, dict) else []
        top_candidate = dict(latest_candidates[0]) if latest_candidates else {}
        latest_valid_count = int(latest.get("valid_count", 0)) if isinstance(latest, dict) else 0
        next_actions: list[str] = []
        gate_blocked_reasons = list(latest.get("gate_blocked_reasons", [])) if isinstance(latest, dict) else []
        if latest_valid_count <= 0:
            next_actions = [
                "lower_min_score_for_observation",
                "inspect_volume_multiplier",
                "inspect_lookback",
                "wait_for_setup",
            ]
        elif gate_blocked_reasons:
            next_actions = [
                "inspect_gate_blocked_reasons",
                "inspect_symbol_rules_alignment",
                "rerun_dry_gate_only",
            ]
        else:
            next_actions = [
                "continue_observation",
                "rerun_next_scan_window",
            ]
        return {
            "total_scans": len(rows),
            "latest_scan_id": str(latest.get("scan_id", "")) if isinstance(latest, dict) else "",
            "latest_valid_count": latest_valid_count,
            "top_candidate": top_candidate,
            "common_rejection_reasons": common_rejections,
            "next_actions": next_actions,
            "gate_blocked_reasons": gate_blocked_reasons,
            "safe_to_live": False,
        }


class ScanObservationJournal:
    def __init__(self, *, max_results: int = 1000):
        self.max_results = max(100, int(max_results))
        self._results: list[dict[str, Any]] = []
        self._sequence = 0

    def append_scan_observation(
        self,
        *,
        observation_id: str = "",
        source_scan_id: str = "",
        market_data_source: str = "mock",
        strategy_name: str = "right_breakout_v01",
        symbols: Optional[list[Any]] = None,
        horizons: Optional[list[int]] = None,
        candidate_outcomes: Optional[list[Any]] = None,
        rejected_outcomes: Optional[list[Any]] = None,
        summary: Optional[dict[str, Any]] = None,
        warnings: Optional[list[Any]] = None,
    ) -> dict[str, Any]:
        self._sequence += 1
        resolved_observation_id = str(observation_id or f"OBS-{self._sequence}")
        row = {
            "observation_id": resolved_observation_id,
            "source_scan_id": str(source_scan_id or ""),
            "market_data_source": str(market_data_source or "mock"),
            "strategy_name": str(strategy_name or "right_breakout_v01"),
            "symbols": [str(item or "").strip().upper() for item in list(symbols or []) if str(item or "").strip()],
            "horizons": [max(1, int(item)) for item in list(horizons or [5, 15, 30]) if int(item) > 0],
            "candidate_outcomes": [dict(item) for item in list(candidate_outcomes or []) if isinstance(item, dict)],
            "rejected_outcomes": [dict(item) for item in list(rejected_outcomes or []) if isinstance(item, dict)],
            "summary": dict(summary or {}),
            "warnings": [str(item) for item in list(warnings or []) if str(item)],
            "safe_to_live": False,
        }
        self._results.append(row)
        if len(self._results) > self.max_results:
            self._results = self._results[-self.max_results :]
        return dict(row)

    def list_scan_observations(
        self,
        *,
        source_scan_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        rows = [dict(item) for item in self._results]
        if source_scan_id not in (None, ""):
            key = str(source_scan_id).strip()
            rows = [item for item in rows if str(item.get("source_scan_id", "")).strip() == key]
        return rows


def _normalize_timestamp(value: Optional[Any]) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if value not in (None, ""):
        return str(value)
    return now_iso()


def _normalize_issues(issues: Optional[list[Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in issues or []:
        if isinstance(item, dict):
            normalized.append({str(key): value for key, value in item.items()})
        else:
            normalized.append({"code": "unknown_issue", "message": str(item)})
    return normalized


def _to_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)
