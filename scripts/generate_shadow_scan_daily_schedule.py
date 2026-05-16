from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_bool(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def generate_shadow_scan_daily_schedule(
    *,
    shadow_scan_universe_summary_json: str = "reports/shadow_scan_universe/summary.json",
    kline_cache_backfill_summary_json: str = "reports/kline_cache_backfill/summary.json",
    shadow_sample_quality_dashboard_json: str = "reports/shadow_sample_quality/shadow_sample_quality_dashboard.json",
    testnet_dry_run_readiness_report_json: str = "reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json",
    operator_checklist_json: str = "reports/daily_operator_checklist/operator_checklist.json",
    output_dir: str = "reports/shadow_scan_schedule",
) -> dict[str, Any]:
    universe_summary = _read_json(Path(shadow_scan_universe_summary_json))
    backfill_summary = _read_json(Path(kline_cache_backfill_summary_json))
    quality_dashboard = _read_json(Path(shadow_sample_quality_dashboard_json))
    readiness_report = _read_json(Path(testnet_dry_run_readiness_report_json))
    operator_checklist = _read_json(Path(operator_checklist_json))

    missing_inputs: list[str] = []
    for label, payload in [
        ("shadow_scan_universe_summary", universe_summary),
        ("kline_cache_backfill_summary", backfill_summary),
        ("shadow_sample_quality_dashboard", quality_dashboard),
        ("testnet_dry_run_readiness_report", readiness_report),
    ]:
        if not payload:
            missing_inputs.append(label)

    universe_rows = int(universe_summary.get("total_rows", 0) or 0)
    max_symbols = max(1, min(20, universe_rows if universe_rows > 0 else 12))

    allow_testnet_dry_run = _as_bool(readiness_report.get("allow_testnet_dry_run"))
    allow_testnet_submit = _as_bool(readiness_report.get("allow_testnet_submit"))
    allow_real_submit = _as_bool(readiness_report.get("allow_real_submit"))

    submit_allowed = bool(allow_testnet_submit)
    real_submit_allowed = bool(allow_real_submit)
    if real_submit_allowed:
        # Safety rail: this planner is shadow-only scheduler.
        real_submit_allowed = False
        submit_allowed = False

    allowed_mode = "SHADOW_ONLY"
    if allow_testnet_dry_run and (not submit_allowed):
        allowed_mode = "DRY_RUN_ONLY"

    base_backfill_cmd = (
        "PYTHONPATH=. ./.venv/bin/python scripts/run_public_kline_backfill.py "
        "--plan-csv reports/kline_cache_backfill_plan/kline_cache_backfill_plan.csv "
        "--cache-dir data/cache/klines --max-symbols {max_symbols} --max-bars 1500 "
        "--market futures --dry-run --public-only --json"
    ).format(max_symbols=max_symbols)
    strict_cmd = (
        "PYTHONPATH=. ./.venv/bin/python scripts/run_shadow_universe_collector.py "
        "--universe-csv reports/shadow_scan_universe/shadow_scan_universe.csv "
        "--collector-mode strict --max-candidates 100 --json"
    )
    observation_cmd = (
        "PYTHONPATH=. ./.venv/bin/python scripts/run_shadow_universe_collector.py "
        "--universe-csv reports/shadow_scan_universe/shadow_scan_universe.csv "
        "--collector-mode observation --allow-near-miss --near-miss-threshold 0.75 --max-candidates 100 --json"
    )
    outcome_cmd = (
        "PYTHONPATH=. ./.venv/bin/python scripts/evaluate_shadow_candidate_outcomes.py "
        "--horizons 30,60,120 --primary-horizon 60 --json"
    )
    quality_cmd = "PYTHONPATH=. ./.venv/bin/python scripts/generate_shadow_sample_quality_dashboard.py --json"

    schedule = [
        {
            "step": 1,
            "name": "public_kline_backfill",
            "recommended_time": "09:00",
            "command": base_backfill_cmd,
            "max_symbols": max_symbols,
            "mode": "public-only",
        },
        {
            "step": 2,
            "name": "strict_shadow_collector",
            "recommended_time": "09:10",
            "command": strict_cmd,
            "max_symbols": max_symbols,
            "mode": "shadow-only",
        },
        {
            "step": 3,
            "name": "observation_shadow_collector",
            "recommended_time": "09:20",
            "command": observation_cmd,
            "max_symbols": max_symbols,
            "mode": "shadow-observation-only",
        },
        {
            "step": 4,
            "name": "shadow_outcome_evaluator",
            "recommended_time": "End of day",
            "command": outcome_cmd,
            "max_symbols": max_symbols,
            "mode": "offline",
        },
        {
            "step": 5,
            "name": "shadow_quality_dashboard",
            "recommended_time": "End of day + 5m",
            "command": quality_cmd,
            "max_symbols": max_symbols,
            "mode": "offline",
        },
    ]

    prohibited_actions = [
        "NO_REAL_SUBMIT",
        "NO_TESTNET_SUBMIT",
        "NO_BYPASS_STRATEGY_GATE",
    ]
    checklist_prohibited = operator_checklist.get("prohibited_actions")
    if isinstance(checklist_prohibited, list):
        for item in checklist_prohibited:
            text = str(item or "").strip()
            if text and text not in prohibited_actions:
                prohibited_actions.append(text)

    final_verdict = "PASS"
    if missing_inputs:
        final_verdict = "PARTIAL"
    if submit_allowed or real_submit_allowed:
        final_verdict = "PARTIAL"

    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "allowed_mode": allowed_mode,
        "submit_allowed": bool(submit_allowed),
        "real_submit_allowed": bool(real_submit_allowed),
        "schedule": schedule,
        "prohibited_actions": prohibited_actions,
        "inputs": {
            "shadow_scan_universe_summary_json": shadow_scan_universe_summary_json,
            "kline_cache_backfill_summary_json": kline_cache_backfill_summary_json,
            "shadow_sample_quality_dashboard_json": shadow_sample_quality_dashboard_json,
            "testnet_dry_run_readiness_report_json": testnet_dry_run_readiness_report_json,
            "operator_checklist_json": operator_checklist_json,
        },
        "missing_inputs": missing_inputs,
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "shadow_scan_daily_schedule.json"
    md_path = out_dir / "shadow_scan_daily_schedule.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Scan Daily Schedule",
        "",
        f"- final_verdict: {result['final_verdict']}",
        f"- allowed_mode: {result['allowed_mode']}",
        f"- submit_allowed: {result['submit_allowed']}",
        f"- real_submit_allowed: {result['real_submit_allowed']}",
        f"- schedule_steps: {len(schedule)}",
    ]
    if missing_inputs:
        lines.append(f"- missing_inputs: {', '.join(missing_inputs)}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result["json_path"] = str(json_path)
    result["md_path"] = str(md_path)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate daily shadow scan schedule")
    parser.add_argument("--shadow-scan-universe-summary-json", default="reports/shadow_scan_universe/summary.json")
    parser.add_argument("--kline-cache-backfill-summary-json", default="reports/kline_cache_backfill/summary.json")
    parser.add_argument("--shadow-sample-quality-dashboard-json", default="reports/shadow_sample_quality/shadow_sample_quality_dashboard.json")
    parser.add_argument("--testnet-dry-run-readiness-report-json", default="reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json")
    parser.add_argument("--operator-checklist-json", default="reports/daily_operator_checklist/operator_checklist.json")
    parser.add_argument("--output-dir", default="reports/shadow_scan_schedule")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_scan_daily_schedule(
        shadow_scan_universe_summary_json=str(args.shadow_scan_universe_summary_json or "reports/shadow_scan_universe/summary.json"),
        kline_cache_backfill_summary_json=str(args.kline_cache_backfill_summary_json or "reports/kline_cache_backfill/summary.json"),
        shadow_sample_quality_dashboard_json=str(
            args.shadow_sample_quality_dashboard_json or "reports/shadow_sample_quality/shadow_sample_quality_dashboard.json"
        ),
        testnet_dry_run_readiness_report_json=str(
            args.testnet_dry_run_readiness_report_json or "reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json"
        ),
        operator_checklist_json=str(args.operator_checklist_json or "reports/daily_operator_checklist/operator_checklist.json"),
        output_dir=str(args.output_dir or "reports/shadow_scan_schedule"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"allowed_mode={result.get('allowed_mode', '')}")


if __name__ == "__main__":
    main()
