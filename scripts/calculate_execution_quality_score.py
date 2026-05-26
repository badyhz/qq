from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.execution_guards import assert_dry_run_required, normalize_execution_mode


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_bool(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y"}


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError:
        return []


def _score_row(row: dict[str, Any]) -> dict[str, Any]:
    entry_status = str(row.get("entry_status", "")).strip().upper()
    protective_ok = _to_bool(row.get("protective_order_success", False))
    outcome = str(row.get("outcome", "")).strip().upper()
    orphan_ever = _to_bool(row.get("orphan_ever_detected", False))
    orphan_after = _to_bool(row.get("orphan_after_close", False))
    orphan_cleanup = _to_bool(row.get("orphan_cleanup_done", False))
    lifecycle_status = str(row.get("lifecycle_status", "")).strip().upper()
    execution_verdict = str(row.get("execution_verdict", "")).strip().upper()
    pnl_usdt = _to_float(row.get("pnl_estimate_usdt", 0.0), 0.0)
    pnl_pct = _to_float(row.get("pnl_pct_estimate", 0.0), 0.0)
    sl_id = str(row.get("sl_order_id", "")).strip()
    tp_id = str(row.get("tp_order_id", "")).strip()
    sl_price = _to_float(row.get("sl_price", 0.0), 0.0)
    tp_price = _to_float(row.get("tp_price", 0.0), 0.0)
    exit_order_id = str(row.get("exit_order_id", "")).strip()

    score_entry = 20 if entry_status in {"SUBMITTED", "FILLED"} else 0
    score_protection = 25 if protective_ok and bool(sl_id) and bool(tp_id) and sl_price > 0 and tp_price > 0 else 0

    clear_outcomes = {"TAKE_PROFIT_TRIGGERED", "STOP_LOSS_TRIGGERED", "MANUAL_FLATTENED", "STILL_OPEN"}
    score_outcome = 20 if outcome in clear_outcomes else 0
    if outcome in {"UNKNOWN", "EXTERNAL_CLOSED"} and exit_order_id:
        score_outcome = 10

    score_orphan = 15
    if orphan_after:
        score_orphan = 0
    elif orphan_ever and orphan_cleanup:
        score_orphan = 10
    elif orphan_ever and not orphan_cleanup:
        score_orphan = 0

    score_pnl = 10 if (str(row.get("pnl_estimate_usdt", "")).strip() and str(row.get("pnl_pct_estimate", "")).strip()) else 0
    if score_pnl == 0 and pnl_usdt == 0.0 and pnl_pct == 0.0 and outcome == "STILL_OPEN":
        score_pnl = 10

    score_state = 10 if lifecycle_status in {"OPEN", "CLOSED"} and execution_verdict in {"PASS", "PARTIAL"} else 0

    total = score_entry + score_protection + score_outcome + score_orphan + score_pnl + score_state

    final_verdict = "PASS"
    if orphan_after:
        final_verdict = "FAIL"
    elif total < 70:
        final_verdict = "FAIL"
    elif total < 85 or outcome in {"UNKNOWN", "EXTERNAL_CLOSED"}:
        final_verdict = "PARTIAL"

    return {
        **row,
        "entry_score": score_entry,
        "protection_score": score_protection,
        "outcome_score": score_outcome,
        "orphan_control_score": score_orphan,
        "pnl_record_score": score_pnl,
        "state_machine_score": score_state,
        "execution_quality_score": total,
        "final_verdict": final_verdict,
        "winning_trade": pnl_usdt > 0,
        "losing_trade": pnl_usdt < 0,
    }


def calculate_execution_quality_score(
    *,
    input_csv: str = "reports/trade_lifecycle/trade_lifecycle.csv",
    output_dir: str = "reports/execution_quality",
) -> dict[str, Any]:
    csv_path = Path(input_csv)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = _read_rows(csv_path)
    scored_rows = [_score_row(row) for row in rows]

    scores_csv = out_dir / "execution_quality_scores.csv"
    summary_json = out_dir / "execution_quality_summary.json"
    summary_md = out_dir / "summary.md"

    score_fieldnames = [
        "trade_id",
        "candidate_id",
        "symbol",
        "outcome",
        "execution_quality_score",
        "final_verdict",
        "entry_score",
        "protection_score",
        "outcome_score",
        "orphan_control_score",
        "pnl_record_score",
        "state_machine_score",
        "orphan_ever_detected",
        "orphan_after_close",
        "orphan_cleanup_done",
        "pnl_estimate_usdt",
        "pnl_pct_estimate",
    ]
    with scores_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=score_fieldnames)
        writer.writeheader()
        for row in scored_rows:
            writer.writerow({key: row.get(key, "") for key in score_fieldnames})

    score_values = [int(row.get("execution_quality_score", 0) or 0) for row in scored_rows]
    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_csv": str(csv_path),
        "total_rows": len(scored_rows),
        "pass_count": sum(1 for row in scored_rows if str(row.get("final_verdict", "")).upper() == "PASS"),
        "partial_count": sum(1 for row in scored_rows if str(row.get("final_verdict", "")).upper() == "PARTIAL"),
        "fail_count": sum(1 for row in scored_rows if str(row.get("final_verdict", "")).upper() == "FAIL"),
        "avg_execution_quality_score": round(sum(score_values) / len(score_values), 4) if score_values else 0.0,
        "min_execution_quality_score": min(score_values) if score_values else 0,
        "max_execution_quality_score": max(score_values) if score_values else 0,
        "winning_count": sum(1 for row in scored_rows if bool(row.get("winning_trade", False))),
        "losing_count": sum(1 for row in scored_rows if bool(row.get("losing_trade", False))),
        "scores_csv": str(scores_csv),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary["final_verdict"] = "PASS"
    if summary["fail_count"] > 0:
        summary["final_verdict"] = "FAIL"
    elif summary["partial_count"] > 0 or summary["total_rows"] == 0:
        summary["final_verdict"] = "PARTIAL"

    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_lines = [
        "# Execution Quality Summary",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- total_rows: {summary['total_rows']}",
        f"- pass_count: {summary['pass_count']}",
        f"- partial_count: {summary['partial_count']}",
        f"- fail_count: {summary['fail_count']}",
        f"- avg_execution_quality_score: {summary['avg_execution_quality_score']}",
        "",
        f"- scores_csv: {scores_csv}",
        f"- summary_json: {summary_json}",
    ]
    summary_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Calculate execution quality score from trade lifecycle CSV")
    parser.add_argument("--input-csv", default="reports/trade_lifecycle/trade_lifecycle.csv")
    parser.add_argument("--output-dir", default="reports/execution_quality")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    mode = normalize_execution_mode(os.environ.get("QQ_RUNTIME_MODE"))
    assert_dry_run_required(mode)

    args = build_arg_parser().parse_args()
    summary = calculate_execution_quality_score(
        input_csv=str(args.input_csv or "reports/trade_lifecycle/trade_lifecycle.csv"),
        output_dir=str(args.output_dir or "reports/execution_quality"),
    )
    if bool(args.json):
        print(json.dumps(summary, ensure_ascii=False))
        return
    print(f"final_verdict={summary.get('final_verdict', '')}")
    print(f"avg_execution_quality_score={summary.get('avg_execution_quality_score', 0.0)}")
    print(f"scores_csv={summary.get('scores_csv', '')}")


if __name__ == "__main__":
    main()
