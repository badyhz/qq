from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    except OSError:
        return []
    return rows


def _parse_reasons(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    return [item.strip() for item in text.split(";") if item.strip()]


def generate_gate_decision_dashboard(
    *,
    gate_audit_jsonl: str = "logs/gate_audit/gate_audit.jsonl",
    gate_replay_csv: str = "reports/gate_replay/gate_replay_results.csv",
    system_health_json: str = "reports/system_health/trading_system_health_dashboard.json",
    output_dir: str = "reports/gate_dashboard",
) -> dict[str, Any]:
    audit_rows = _load_jsonl(Path(gate_audit_jsonl))
    replay_rows = read_csv_rows(Path(gate_replay_csv))
    system_health = _load_json(Path(system_health_json))

    by_decision = Counter()
    by_reason = Counter()
    by_symbol_blocked = Counter()

    for row in replay_rows:
        decision = str(row.get("gate_decision", "BLOCK_UNKNOWN")).strip().upper()
        blocked = str(row.get("would_block", "")).strip().lower() in {"1", "true", "yes", "y"}
        reasons = _parse_reasons(row.get("reason", ""))
        by_decision[decision] += 1
        for item in reasons:
            by_reason[item] += 1
        if blocked:
            symbol = str(row.get("symbol", "")).strip().upper()
            if symbol:
                by_symbol_blocked[symbol] += 1

    if not replay_rows:
        for row in audit_rows:
            decision = str(row.get("gate_decision", "BLOCK_UNKNOWN")).strip().upper()
            by_decision[decision] += 1
            reasons = _parse_reasons(row.get("reason", []))
            for item in reasons:
                by_reason[item] += 1
            if decision.startswith("BLOCK_"):
                symbol = str(row.get("symbol", "")).strip().upper()
                if symbol:
                    by_symbol_blocked[symbol] += 1

    blocked_count = sum(
        1
        for row in replay_rows
        if str(row.get("would_block", "")).strip().lower() in {"1", "true", "yes", "y"}
    )
    submit_allowed_count = sum(
        1
        for row in replay_rows
        if str(row.get("submit_allowed", "")).strip().lower() in {"1", "true", "yes", "y"}
    )
    dry_run_allowed_count = sum(
        1
        for row in replay_rows
        if (str(row.get("would_block", "")).strip().lower() in {"1", "true", "yes", "y"})
        and (str(row.get("dry_run_allowed", "")).strip().lower() in {"1", "true", "yes", "y"})
    )
    if not replay_rows:
        blocked_count = sum(1 for row in audit_rows if str(row.get("gate_decision", "")).strip().upper().startswith("BLOCK_"))
        submit_allowed_count = sum(1 for row in audit_rows if bool(row.get("submit_allowed", False)))
        dry_run_allowed_count = sum(
            1
            for row in audit_rows
            if str(row.get("gate_decision", "")).strip().upper().startswith("BLOCK_") and bool(row.get("dry_run_allowed", False))
        )

    system_health_verdict = str(system_health.get("final_verdict", "UNKNOWN")).strip().upper()
    operator_attention: list[str] = []
    if by_decision.get("BLOCK_LOW_SAMPLE", 0) > 0:
        operator_attention.append("LOW_SAMPLE dominates gate blocks; collect more samples before submit.")
    if by_decision.get("BLOCK_SYSTEM_HEALTH", 0) > 0 or system_health_verdict == "FAIL":
        operator_attention.append("System health gate blocks present; resolve health issues before any submit.")
    if by_decision.get("BLOCK_UNKNOWN", 0) > 0:
        operator_attention.append("Unknown gate blocks found; verify missing reports and gate inputs.")
    if not operator_attention:
        operator_attention.append("Gate decisions stable; continue dry-run monitoring.")

    final_verdict = "PASS"
    if by_decision.get("BLOCK_SYSTEM_HEALTH", 0) > 0 or system_health_verdict == "FAIL":
        final_verdict = "FAIL"
    elif blocked_count > 0 or by_decision.get("BLOCK_UNKNOWN", 0) > 0:
        final_verdict = "PARTIAL"

    top_blocked_symbols = [{"symbol": symbol, "blocked_count": int(count)} for symbol, count in by_symbol_blocked.most_common(5)]

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dashboard_json = out_dir / "gate_decision_dashboard.json"
    by_decision_csv = out_dir / "by_decision.csv"
    by_reason_csv = out_dir / "by_reason.csv"
    by_symbol_csv = out_dir / "by_symbol.csv"
    summary_md = out_dir / "summary.md"

    with by_decision_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["decision", "count"])
        writer.writeheader()
        for key, count in sorted(by_decision.items(), key=lambda kv: kv[0]):
            writer.writerow({"decision": key, "count": int(count)})

    with by_reason_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["reason", "count"])
        writer.writeheader()
        for key, count in by_reason.most_common():
            writer.writerow({"reason": key, "count": int(count)})

    with by_symbol_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["symbol", "blocked_count"])
        writer.writeheader()
        for item in top_blocked_symbols:
            writer.writerow(item)

    dashboard = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "audit_count": len(audit_rows),
        "replay_candidate_count": len(replay_rows),
        "submit_allowed_count": submit_allowed_count,
        "blocked_count": blocked_count,
        "dry_run_allowed_count": dry_run_allowed_count,
        "by_decision": {key: int(value) for key, value in sorted(by_decision.items(), key=lambda kv: kv[0])},
        "by_reason": {key: int(value) for key, value in by_reason.most_common()},
        "top_blocked_symbols": top_blocked_symbols,
        "system_health_verdict": system_health_verdict or "UNKNOWN",
        "operator_attention": operator_attention,
        "source_paths": {
            "gate_audit_jsonl": gate_audit_jsonl,
            "gate_replay_csv": gate_replay_csv,
            "system_health_json": system_health_json,
        },
        "output_paths": {
            "dashboard_json": str(dashboard_json),
            "by_decision_csv": str(by_decision_csv),
            "by_reason_csv": str(by_reason_csv),
            "by_symbol_csv": str(by_symbol_csv),
            "summary_md": str(summary_md),
        },
    }
    dashboard_json.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Gate Decision Dashboard",
        "",
        f"- final_verdict: {dashboard['final_verdict']}",
        f"- audit_count: {dashboard['audit_count']}",
        f"- replay_candidate_count: {dashboard['replay_candidate_count']}",
        f"- blocked_count: {dashboard['blocked_count']}",
        f"- submit_allowed_count: {dashboard['submit_allowed_count']}",
        f"- dry_run_allowed_count: {dashboard['dry_run_allowed_count']}",
        f"- system_health_verdict: {dashboard['system_health_verdict']}",
        "",
        "## Operator Attention",
    ]
    for item in operator_attention:
        lines.append(f"- {item}")
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dashboard


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate gate decision dashboard from audit and replay outputs")
    parser.add_argument("--gate-audit-jsonl", default="logs/gate_audit/gate_audit.jsonl")
    parser.add_argument("--gate-replay-csv", default="reports/gate_replay/gate_replay_results.csv")
    parser.add_argument("--system-health-json", default="reports/system_health/trading_system_health_dashboard.json")
    parser.add_argument("--output-dir", default="reports/gate_dashboard")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_gate_decision_dashboard(
        gate_audit_jsonl=str(args.gate_audit_jsonl or "logs/gate_audit/gate_audit.jsonl"),
        gate_replay_csv=str(args.gate_replay_csv or "reports/gate_replay/gate_replay_results.csv"),
        system_health_json=str(args.system_health_json or "reports/system_health/trading_system_health_dashboard.json"),
        output_dir=str(args.output_dir or "reports/gate_dashboard"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', 'UNKNOWN')}")
    print(f"blocked_count={result.get('blocked_count', 0)}")
    print(f"dashboard_json={result.get('output_paths', {}).get('dashboard_json', '')}")


if __name__ == "__main__":
    main()
