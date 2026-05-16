from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core.execution_candidate_queue import load_candidates
from scripts.strategy_edge_common import read_jsonl_rows


def _parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _parse_symbols(text: str) -> list[str]:
    return [item.strip().upper() for item in str(text or "").split(",") if item.strip()]


def _latest_replay_batch_summary() -> dict[str, Any]:
    root = Path("logs")
    if not root.exists():
        return {}
    candidates = list(root.glob("replay_batch_*/summary.json"))
    if not candidates:
        candidates = list(root.glob("replay_batch*/summary.json"))
    if not candidates:
        return {}
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _recommended_actions(per_symbol_state: list[dict[str, Any]], candidate_summary: dict[str, int]) -> list[str]:
    actions: list[str] = []
    statuses = {str(row.get("protection_status", "")) for row in per_symbol_state}
    if statuses == {"FULLY_PROTECTED"}:
        actions.append("no_action")
    if "ORPHAN_PROTECTION" in statuses:
        actions.append("review_orphan_protection")
    if "PARTIAL_PROTECTED" in statuses:
        actions.append("repair_partial_protection")
    if int(candidate_summary.get("pending", 0)) > 0:
        actions.append("review_candidates")
    if "FLAT_CLEAN" in statuses:
        actions.append("run_batch_dry_run")
    if "NAKED_POSITION" in statuses:
        actions.append("manual_cleanup_required")
    if not actions:
        actions.append("no_action")
    return actions


def _load_state_map(state_jsonl: str) -> dict[str, dict[str, Any]]:
    if not state_jsonl:
        return {}
    path = Path(state_jsonl)
    if not path.exists():
        return {}
    state_map: dict[str, dict[str, Any]] = {}
    for row in read_jsonl_rows(path):
        symbol = str(row.get("symbol", "")).strip().upper()
        if symbol:
            state_map[symbol] = dict(row)
    return state_map


def _normalize_symbol_state(symbol: str, state_row: dict[str, Any] | None) -> dict[str, Any]:
    if not state_row:
        return {
            "symbol": symbol,
            "positionAmt": 0.0,
            "entryPrice": 0.0,
            "markPrice": 0.0,
            "open_stop_market_count": 0,
            "open_take_profit_market_count": 0,
            "protection_status": "preflight_unavailable",
            "action_required": "state_jsonl_missing_or_symbol_not_found",
            "error_code": "readonly_state_missing",
            "error_message": "readonly mode requires precomputed state jsonl",
        }
    return {
        "symbol": symbol,
        "positionAmt": state_row.get("positionAmt", state_row.get("position_amt", 0.0)),
        "entryPrice": state_row.get("entryPrice", state_row.get("entry_price", 0.0)),
        "markPrice": state_row.get("markPrice", state_row.get("mark_price", 0.0)),
        "open_stop_market_count": state_row.get("open_stop_market_count", 0),
        "open_take_profit_market_count": state_row.get("open_take_profit_market_count", 0),
        "protection_status": state_row.get("protection_status", "preflight_unavailable"),
        "action_required": state_row.get("action_required", ""),
        "error_code": state_row.get("error_code", ""),
        "error_message": state_row.get("error_message", ""),
    }


def build_observation_shift_summary(
    *,
    env: str,
    symbols: str,
    shift_id: str = "",
    state_jsonl: str = "",
    risk_events_jsonl: str = "logs/risk_events.jsonl",
    candidates_jsonl: str = "logs/execution_candidates.jsonl",
    dry_run: bool = True,
    lookback_minutes: int = 120,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    resolved_shift_id = str(shift_id or started_at.strftime("shift_%Y%m%d_%H%M%S"))
    symbol_list = _parse_symbols(symbols)

    state_map = _load_state_map(state_jsonl)
    per_symbol_state = [_normalize_symbol_state(symbol, state_map.get(symbol)) for symbol in symbol_list]

    risk_rows = []
    try:
        risk_rows = read_jsonl_rows(Path(risk_events_jsonl))
    except Exception:
        risk_rows = []
    lookback_cutoff = started_at - timedelta(minutes=max(1, int(lookback_minutes)))
    recent_events: list[dict[str, Any]] = []
    count_by_severity: dict[str, int] = {}
    for row in risk_rows:
        ts = _parse_dt(row.get("ts_utc", ""))
        if ts is None or ts < lookback_cutoff:
            continue
        severity = str(row.get("severity", "UNKNOWN")).upper()
        count_by_severity[severity] = int(count_by_severity.get(severity, 0)) + 1
        recent_events.append(
            {
                "ts_utc": row.get("ts_utc", ""),
                "severity": severity,
                "event_type": row.get("event_type", ""),
                "symbol": row.get("symbol", ""),
                "message": row.get("message", ""),
            }
        )
    recent_events = recent_events[-10:]

    candidates = []
    try:
        candidates = load_candidates(candidates_jsonl)
    except Exception:
        candidates = []
    candidate_summary = {
        "total": len(candidates),
        "pending": 0,
        "approved": 0,
        "rejected": 0,
        "expired": 0,
        "submitted": 0,
        "skipped": 0,
    }
    for row in candidates:
        status = str(row.get("status", "")).strip().upper()
        key = status.lower()
        if key in candidate_summary:
            candidate_summary[key] = int(candidate_summary[key]) + 1

    replay_batch_summary = _latest_replay_batch_summary()
    actions = _recommended_actions(per_symbol_state, candidate_summary)

    return {
        "shift_id": resolved_shift_id,
        "env": str(env or "").strip().lower(),
        "started_at_utc": started_at.isoformat(),
        "symbols": symbol_list,
        "state_source": str(state_jsonl or "MISSING"),
        "per_symbol_state": per_symbol_state,
        "recent_risk_events": {
            "count_by_severity": count_by_severity,
            "latest_events": recent_events,
        },
        "execution_candidates": candidate_summary,
        "latest_replay_batch_summary": replay_batch_summary,
        "recommended_actions": actions,
        "dry_run": bool(dry_run),
    }


def render_observation_shift_markdown(summary: dict[str, Any]) -> str:
    per_symbol_state = list(summary.get("per_symbol_state", []))
    count_by_severity = dict(summary.get("recent_risk_events", {}).get("count_by_severity", {}))
    candidate_summary = dict(summary.get("execution_candidates", {}))
    actions = list(summary.get("recommended_actions", []))
    md_lines = [
        "# Observation Shift Summary",
        "",
        f"- shift_id: {summary.get('shift_id', '')}",
        f"- env: {summary.get('env', '')}",
        f"- started_at_utc: {summary.get('started_at_utc', '')}",
        f"- state_source: {summary.get('state_source', 'MISSING')}",
        "",
        "## Per Symbol State",
        "| symbol | protection_status | positionAmt | entryPrice | markPrice | open_stop | open_tp | action_required |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in per_symbol_state:
        md_lines.append(
            "| {symbol} | {protection_status} | {positionAmt} | {entryPrice} | {markPrice} | {open_stop_market_count} | {open_take_profit_market_count} | {action_required} |".format(**row)
        )
    md_lines.extend(
        [
            "",
            "## Risk Events",
            f"- count_by_severity: {json.dumps(count_by_severity, ensure_ascii=False)}",
            "",
            "## Execution Candidates",
            f"- {json.dumps(candidate_summary, ensure_ascii=False)}",
            "",
            "## Recommended Actions",
        ]
    )
    for action in actions:
        md_lines.append(f"- {action}")
    return "\n".join(md_lines) + "\n"


def write_observation_shift_outputs(summary: dict[str, Any], output_dir: str) -> dict[str, Any]:
    shift_id = str(summary.get("shift_id", "")).strip() or datetime.now(timezone.utc).strftime("shift_%Y%m%d_%H%M%S")
    shift_dir = Path(output_dir) / shift_id
    shift_dir.mkdir(parents=True, exist_ok=True)
    summary_json = shift_dir / "summary.json"
    summary_md = shift_dir / "summary.md"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_md.write_text(render_observation_shift_markdown(summary), encoding="utf-8")
    output = dict(summary)
    output["summary_json"] = str(summary_json)
    output["summary_md"] = str(summary_md)
    return output


def run_observation_shift(
    *,
    env: str,
    symbols: str,
    shift_id: str = "",
    state_jsonl: str = "",
    risk_events_jsonl: str = "logs/risk_events.jsonl",
    candidates_jsonl: str = "logs/execution_candidates.jsonl",
    output_dir: str = "logs/observation_shifts",
    dry_run: bool = True,
    lookback_minutes: int = 120,
) -> dict[str, Any]:
    summary = build_observation_shift_summary(
        env=env,
        symbols=symbols,
        shift_id=shift_id,
        state_jsonl=state_jsonl,
        risk_events_jsonl=risk_events_jsonl,
        candidates_jsonl=candidates_jsonl,
        dry_run=dry_run,
        lookback_minutes=lookback_minutes,
    )
    return write_observation_shift_outputs(summary, output_dir)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one observation shift summary")
    parser.add_argument("--env", default="testnet")
    parser.add_argument("--symbols", default="FETUSDT,OPUSDT")
    parser.add_argument("--shift-id", default="")
    parser.add_argument("--state-jsonl", default="")
    parser.add_argument("--risk-events-jsonl", default="logs/risk_events.jsonl")
    parser.add_argument("--candidates-jsonl", default="logs/execution_candidates.jsonl")
    parser.add_argument("--output-dir", default="logs/observation_shifts")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--lookback-minutes", type=int, default=120)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = run_observation_shift(
        env=str(args.env or "testnet"),
        symbols=str(args.symbols or ""),
        shift_id=str(args.shift_id or ""),
        state_jsonl=str(args.state_jsonl or ""),
        risk_events_jsonl=str(args.risk_events_jsonl or "logs/risk_events.jsonl"),
        candidates_jsonl=str(args.candidates_jsonl or "logs/execution_candidates.jsonl"),
        output_dir=str(args.output_dir or "logs/observation_shifts"),
        dry_run=bool(args.dry_run),
        lookback_minutes=int(args.lookback_minutes or 120),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"shift_id={result.get('shift_id', '')}")
    print(f"env={result.get('env', '')}")
    print(f"summary_json={result.get('summary_json', '')}")
    print(f"summary_md={result.get('summary_md', '')}")


if __name__ == "__main__":
    main()
