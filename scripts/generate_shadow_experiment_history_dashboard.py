from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


BY_EXPERIMENT_FIELDS = [
    "experiment_id",
    "strategy_key",
    "symbol",
    "side",
    "timeframe",
    "experiment_type",
    "history_run_count",
    "sample_count",
    "evaluated_count",
    "promotion_decision",
    "stability_score",
    "stability_verdict",
    "dashboard_verdict",
    "next_action",
    "reason",
]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_avg(values: list[float]) -> float:
    valid = [value for value in values if math.isfinite(value)]
    if not valid:
        return float("nan")
    return sum(valid) / len(valid)


def _to_int(value: Any, default: int = 0) -> int:
    parsed = to_float_nan(value)
    if not math.isfinite(parsed):
        return int(default)
    return int(parsed)


def generate_shadow_experiment_history_dashboard(
    *,
    experiment_history_csv: str = "reports/shadow_experiment_history/experiment_history.csv",
    stability_scores_csv: str = "reports/shadow_experiment_stability/stability_scores.csv",
    experiment_promotion_decisions_csv: str = "reports/shadow_experiment_promotion/experiment_promotion_decisions.csv",
    experiment_eod_report_json: str = "reports/shadow_experiment_eod/experiment_eod_report.json",
    output_dir: str = "reports/shadow_experiment_history_dashboard",
) -> dict[str, Any]:
    history_rows = read_csv_rows(Path(experiment_history_csv))
    stability_rows = read_csv_rows(Path(stability_scores_csv))
    promotion_rows = read_csv_rows(Path(experiment_promotion_decisions_csv))
    eod = _read_json(Path(experiment_eod_report_json))

    history_by_exp: dict[str, list[dict[str, Any]]] = {}
    for row in history_rows:
        exp_id = str(row.get("experiment_id", "")).strip()
        if exp_id:
            history_by_exp.setdefault(exp_id, []).append(row)

    stability_by_exp: dict[str, dict[str, Any]] = {
        str(row.get("experiment_id", "")).strip(): row
        for row in stability_rows
        if str(row.get("experiment_id", "")).strip()
    }
    promotion_by_exp: dict[str, dict[str, Any]] = {
        str(row.get("experiment_id", "")).strip(): row
        for row in promotion_rows
        if str(row.get("experiment_id", "")).strip()
    }

    experiment_ids = sorted(set(history_by_exp.keys()) | set(stability_by_exp.keys()) | set(promotion_by_exp.keys()))
    by_rows: list[dict[str, Any]] = []
    for exp_id in experiment_ids:
        hrows = sorted(
            history_by_exp.get(exp_id, []),
            key=lambda row: (str(row.get("run_date", "")), str(row.get("created_at", ""))),
        )
        latest = hrows[-1] if hrows else {}
        stability = stability_by_exp.get(exp_id, {})
        promotion = promotion_by_exp.get(exp_id, {})
        sample_count = _to_int(latest.get("sample_count"), _to_int(promotion.get("sample_count"), 0))
        evaluated_count = _to_int(latest.get("evaluated_count"), 0)
        stability_score = to_float_nan(stability.get("stability_score"))
        stability_verdict = str(stability.get("stability_verdict", "NEEDS_MORE_DATA")).strip().upper() or "NEEDS_MORE_DATA"
        promotion_decision = str(promotion.get("promotion_decision", "KEEP_COLLECTING")).strip().upper() or "KEEP_COLLECTING"

        reasons: list[str] = []
        dashboard_verdict = "PARTIAL"
        next_action = "KEEP_COLLECTING_SHADOW_SAMPLES"
        if stability_verdict == "STABLE_PROMISING" and promotion_decision.startswith("PROMOTE_"):
            dashboard_verdict = "PASS"
            next_action = "CONTINUE_OBSERVATION_WITH_CURRENT_RULES"
            reasons.append("promising_but_shadow_only")
        else:
            dashboard_verdict = "PARTIAL"
            if sample_count < 20:
                reasons.append("insufficient_experiment_samples")
            if stability_verdict == "NEEDS_MORE_DATA":
                reasons.append("stability_not_ready")
            if promotion_decision == "KEEP_COLLECTING":
                reasons.append("promotion_keep_collecting")

        base = latest if latest else (promotion if promotion else stability)
        by_rows.append(
            {
                "experiment_id": exp_id,
                "strategy_key": str(base.get("strategy_key", "")).strip(),
                "symbol": str(base.get("symbol", "")).strip().upper(),
                "side": str(base.get("side", "")).strip().upper(),
                "timeframe": str(base.get("timeframe", "5m")).strip() or "5m",
                "experiment_type": str(base.get("experiment_type", "UNKNOWN")).strip().upper() or "UNKNOWN",
                "history_run_count": len(hrows),
                "sample_count": sample_count,
                "evaluated_count": evaluated_count,
                "promotion_decision": promotion_decision,
                "stability_score": round(stability_score, 8) if math.isfinite(stability_score) else float("nan"),
                "stability_verdict": stability_verdict,
                "dashboard_verdict": dashboard_verdict,
                "next_action": next_action,
                "reason": ";".join(sorted(set(reasons))) if reasons else "ok",
            }
        )

    keep_collecting_count = sum(
        1 for row in by_rows if str(row.get("promotion_decision", "")).strip().upper() == "KEEP_COLLECTING"
    )
    promote_count = sum(
        1
        for row in by_rows
        if str(row.get("promotion_decision", "")).strip().upper()
        in {"PROMOTE_TO_SHADOW_OBSERVATION", "PROMOTE_TO_STRICT_CANDIDATE_TEST"}
    )
    reject_count = sum(
        1 for row in by_rows if str(row.get("promotion_decision", "")).strip().upper() == "REJECT_EXPERIMENT"
    )
    needs_more_data_count = sum(
        1 for row in by_rows if str(row.get("stability_verdict", "")).strip().upper() == "NEEDS_MORE_DATA"
    )
    avg_stability_score = _safe_avg([to_float_nan(row.get("stability_score")) for row in by_rows])

    operator_attention: list[str] = []
    if needs_more_data_count > 0:
        operator_attention.append("All experiments need more data before any relaxation decision.")
    if keep_collecting_count == len(by_rows) and by_rows:
        operator_attention.append("All experiments remain in KEEP_COLLECTING state.")

    final_verdict = "PASS"
    if by_rows and (needs_more_data_count > 0 or promote_count == 0):
        final_verdict = "PARTIAL"
    if not by_rows:
        final_verdict = "PARTIAL"
        operator_attention.append("No experiment history rows available.")

    dashboard = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "history_row_count": len(history_rows),
        "experiment_count": len(by_rows),
        "keep_collecting_count": keep_collecting_count,
        "promote_count": promote_count,
        "reject_count": reject_count,
        "needs_more_data_count": needs_more_data_count,
        "avg_stability_score": round(avg_stability_score, 8) if math.isfinite(avg_stability_score) else float("nan"),
        "allowed_mode": "SHADOW_ONLY",
        "submit_allowed": False,
        "real_submit_allowed": False,
        "operator_attention": sorted(set(operator_attention)),
        "eod_final_verdict": str(eod.get("final_verdict", "")).strip().upper() or "UNKNOWN",
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dashboard_json = out_dir / "history_dashboard.json"
    by_csv = out_dir / "by_experiment.csv"
    summary_md = out_dir / "summary.md"

    with by_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BY_EXPERIMENT_FIELDS)
        writer.writeheader()
        for row in by_rows:
            writer.writerow({field: row.get(field, "") for field in BY_EXPERIMENT_FIELDS})

    dashboard_json.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Experiment History Dashboard",
        "",
        f"- final_verdict: {dashboard['final_verdict']}",
        f"- history_row_count: {dashboard['history_row_count']}",
        f"- experiment_count: {dashboard['experiment_count']}",
        f"- keep_collecting_count: {dashboard['keep_collecting_count']}",
        f"- promote_count: {dashboard['promote_count']}",
        f"- reject_count: {dashboard['reject_count']}",
        f"- needs_more_data_count: {dashboard['needs_more_data_count']}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_allowed: false",
        "- real_submit_allowed: false",
    ]
    if dashboard["operator_attention"]:
        lines.append(f"- operator_attention: {', '.join(dashboard['operator_attention'])}")
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dashboard


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate dashboard from shadow experiment history and stability")
    parser.add_argument("--experiment-history-csv", default="reports/shadow_experiment_history/experiment_history.csv")
    parser.add_argument("--stability-scores-csv", default="reports/shadow_experiment_stability/stability_scores.csv")
    parser.add_argument(
        "--experiment-promotion-decisions-csv",
        default="reports/shadow_experiment_promotion/experiment_promotion_decisions.csv",
    )
    parser.add_argument("--experiment-eod-report-json", default="reports/shadow_experiment_eod/experiment_eod_report.json")
    parser.add_argument("--output-dir", default="reports/shadow_experiment_history_dashboard")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_experiment_history_dashboard(
        experiment_history_csv=str(args.experiment_history_csv or "reports/shadow_experiment_history/experiment_history.csv"),
        stability_scores_csv=str(args.stability_scores_csv or "reports/shadow_experiment_stability/stability_scores.csv"),
        experiment_promotion_decisions_csv=str(
            args.experiment_promotion_decisions_csv
            or "reports/shadow_experiment_promotion/experiment_promotion_decisions.csv"
        ),
        experiment_eod_report_json=str(args.experiment_eod_report_json or "reports/shadow_experiment_eod/experiment_eod_report.json"),
        output_dir=str(args.output_dir or "reports/shadow_experiment_history_dashboard"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"experiment_count={result.get('experiment_count', 0)}")


if __name__ == "__main__":
    main()
