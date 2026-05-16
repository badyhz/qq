from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core.execution_candidate_queue import (
    apply_candidate_scoring,
    append_candidate,
    dedupe_candidates,
    expire_old_candidates,
    has_recent_pending_candidate,
    load_candidates,
    make_candidate_id,
    write_candidates,
)
from core.risk_event_logger import log_risk_event
from scripts.strategy_edge_common import read_jsonl_rows


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _parse_csv(value: str) -> list[str]:
    return [item.strip().upper() for item in str(value or "").split(",") if item.strip()]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _load_preflight_state(path: str) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    state_map: dict[str, dict[str, Any]] = {}
    for row in read_jsonl_rows(p):
        sym = str(row.get("symbol", "")).strip().upper()
        if sym:
            state_map[sym] = row
    return state_map


def build_execution_candidates(
    *,
    env: str,
    input_jsonl: str,
    output_jsonl: str,
    symbols: str,
    allowlist: str,
    max_candidates: int = 10,
    ttl_minutes: int = 60,
    dry_run: bool = True,
    json_summary: bool = False,
    allow_duplicate_candidates: bool = False,
    max_symbol_notional_usdt: float = 60.0,
    base_url: str = "",
    preflight_state_jsonl: str = "",
) -> dict[str, Any]:
    resolved_env = str(env or "").strip().lower()
    symbol_filter = set(_parse_csv(symbols))
    allowlist_set = set(_parse_csv(allowlist))
    preflight_state_map = _load_preflight_state(preflight_state_jsonl)

    rows = read_jsonl_rows(Path(input_jsonl))
    existing = dedupe_candidates(load_candidates(output_jsonl))
    existing, expired_count = expire_old_candidates(existing)
    if (not dry_run) and expired_count > 0:
        write_candidates(output_jsonl, existing)

    created = 0
    skipped = 0
    skipped_reasons: dict[str, int] = {}
    appended: list[dict[str, Any]] = []

    for row in rows:
        payload = dict(row.get("testnet_payload", {})) if isinstance(row.get("testnet_payload"), dict) else {}
        symbol = str(row.get("symbol", payload.get("symbol", ""))).strip().upper()
        if symbol_filter and symbol not in symbol_filter:
            continue
        if symbol not in allowlist_set:
            skipped += 1
            skipped_reasons["symbol_not_in_allowlist"] = int(skipped_reasons.get("symbol_not_in_allowlist", 0)) + 1
            continue

        quantity = _to_float(payload.get("quantity", row.get("quantity", 0.0)))
        notional = _to_float(payload.get("notional_usdt", row.get("notional_usdt", 0.0)))
        entry_payload = payload.get("entry", {})
        if quantity <= 0 or notional <= 0:
            skipped += 1
            skipped_reasons["invalid_quantity_or_notional"] = int(skipped_reasons.get("invalid_quantity_or_notional", 0)) + 1
            continue
        if not isinstance(entry_payload, dict) or not entry_payload:
            skipped += 1
            skipped_reasons["missing_entry_payload"] = int(skipped_reasons.get("missing_entry_payload", 0)) + 1
            continue

        if (not allow_duplicate_candidates) and has_recent_pending_candidate(existing + appended, symbol=symbol, ttl_minutes=ttl_minutes):
            skipped += 1
            skipped_reasons["duplicate_pending_within_ttl"] = int(skipped_reasons.get("duplicate_pending_within_ttl", 0)) + 1
            continue

        preflight_status = "preflight_unavailable"
        risk_flags: list[str] = []
        status = "PENDING"
        reason = "ready_for_review"

        if preflight_state_map:
            preflight = preflight_state_map.get(symbol, {})
            if bool(preflight.get("ok", False)):
                preflight_status = str(preflight.get("protection_status", ""))
            else:
                preflight_status = "preflight_unavailable"

            if preflight_status == "FULLY_PROTECTED":
                risk_flags.append("ALREADY_FULLY_PROTECTED")
                status = "SKIPPED"
                reason = "already_fully_protected"
            elif preflight_status == "ORPHAN_PROTECTION":
                risk_flags.append("ORPHAN_PROTECTION")
                status = "SKIPPED"
                reason = "orphan_protection_detected"
            elif preflight_status == "PARTIAL_PROTECTED":
                risk_flags.append("PARTIAL_PROTECTED")
                status = "SKIPPED"
                reason = "partial_protection_detected"
            elif preflight_status == "NAKED_POSITION":
                risk_flags.append("NAKED_POSITION")
                status = "SKIPPED"
                reason = "naked_position_detected"
            elif preflight_status == "preflight_unavailable":
                risk_flags.append("PREFLIGHT_UNAVAILABLE")
                status = "SKIPPED"
                reason = "preflight_unavailable"
        else:
            preflight_status = "PREFLIGHT_SKIPPED"
            risk_flags.append("PREFLIGHT_SKIPPED")
            status = "PENDING"
            reason = "ready_for_review (no preflight check)"

        stop_loss_plan = payload.get("stop_loss_plan", {}) if isinstance(payload.get("stop_loss_plan"), dict) else {}
        take_profit_plan = payload.get("take_profit_plan", {}) if isinstance(payload.get("take_profit_plan"), dict) else {}
        if not stop_loss_plan or not take_profit_plan:
            risk_flags.append("MISSING_PROTECTION_PLAN")

        now = _now_utc()
        expires = now + timedelta(minutes=max(1, int(ttl_minutes)))
        seed = f"{symbol}|{payload.get('source_shadow_timestamp', '')}|{entry_payload.get('price', '')}|{quantity}|{notional}"
        candidate = {
            "candidate_id": make_candidate_id(symbol=symbol, seed=seed),
            "ts_utc": now.isoformat(),
            "source": "replay_payload",
            "env": resolved_env,
            "symbol": symbol,
            "side": str(payload.get("side", "BUY")).upper(),
            "order_type": str(payload.get("type", "MARKET")).upper(),
            "quantity": quantity,
            "notional_usdt": notional,
            "entry_payload": entry_payload,
            "stop_loss_plan": stop_loss_plan,
            "take_profit_plan": take_profit_plan,
            "confidence": payload.get("confidence", ""),
            "reason": reason,
            "status": status,
            "expires_at_utc": expires.isoformat(),
            "preflight_status": preflight_status,
            "risk_flags": risk_flags,
            "approval_required": True,
            "approved_by": "",
            "approved_at_utc": "",
            "submit_result_ref": "",
            "correlation_id": str(payload.get("dry_run_id", payload.get("client_order_id", ""))),
        }
        candidate = apply_candidate_scoring([candidate], max_symbol_notional_usdt=float(max_symbol_notional_usdt), now_utc=now)[0]

        if status == "PENDING":
            created += 1
        else:
            skipped += 1
            skipped_reasons[reason] = int(skipped_reasons.get(reason, 0)) + 1

        appended.append(candidate)
        if len(appended) >= int(max_candidates):
            break

    if not dry_run:
        for row in appended:
            append_candidate(output_jsonl, row)

    summary = {
        "env": resolved_env,
        "input_jsonl": input_jsonl,
        "output_jsonl": output_jsonl,
        "candidates_created": created,
        "candidates_skipped": skipped,
        "skipped_reasons": skipped_reasons,
        "expired_candidates": expired_count,
        "dry_run": bool(dry_run),
        "generated_candidates": appended,
    }

    if skipped > 0:
        log_risk_event(
            env=resolved_env,
            symbol="",
            component="build_execution_candidates",
            event_type="BATCH_SYMBOL_FAILED",
            message="some candidates were skipped during candidate building",
            context={"skipped_reasons": skipped_reasons},
            action_required="review_skipped_reasons",
        )

    if json_summary:
        print(json.dumps(summary, ensure_ascii=False))
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build execution candidates from replay payload JSONL")
    parser.add_argument("--env", default="testnet")
    parser.add_argument("--input-jsonl", default="logs/replayed_testnet_dry_payloads_exchangeinfo.jsonl")
    parser.add_argument("--output-jsonl", default="logs/execution_candidates.jsonl")
    parser.add_argument("--symbols", default="FETUSDT,OPUSDT")
    parser.add_argument("--allowlist", default="FETUSDT,OPUSDT")
    parser.add_argument("--max-candidates", type=int, default=10)
    parser.add_argument("--ttl-minutes", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json-summary", action="store_true")
    parser.add_argument("--allow-duplicate-candidates", action="store_true")
    parser.add_argument("--max-symbol-notional-usdt", type=float, default=60.0)
    parser.add_argument("--base-url", default="")
    parser.add_argument("--preflight-state-jsonl", default="")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    build_execution_candidates(
        env=str(args.env or "testnet"),
        input_jsonl=str(args.input_jsonl or "logs/replayed_testnet_dry_payloads_exchangeinfo.jsonl"),
        output_jsonl=str(args.output_jsonl or "logs/execution_candidates.jsonl"),
        symbols=str(args.symbols or ""),
        allowlist=str(args.allowlist or ""),
        max_candidates=int(args.max_candidates or 10),
        ttl_minutes=int(args.ttl_minutes or 60),
        dry_run=bool(args.dry_run),
        json_summary=bool(args.json_summary),
        allow_duplicate_candidates=bool(args.allow_duplicate_candidates),
        max_symbol_notional_usdt=float(args.max_symbol_notional_usdt or 60.0),
        base_url=str(args.base_url or ""),
        preflight_state_jsonl=str(args.preflight_state_jsonl or ""),
    )


if __name__ == "__main__":
    main()
