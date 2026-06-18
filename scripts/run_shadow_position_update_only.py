"""Phase 10L Shadow Position Update-Only Pipeline.

Manages existing OPEN paper positions without scanning new signals:
  1. Update existing positions with klines (update-only mode)
  2. Legacy quarantine
  3. Clean performance scorecard
  4. Sample collection gate

No new strategy scan. No new TradeIntent. No new PaperPosition.
No orders, no accounts, no secrets, no testnet, no live.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.paper_trading.shadow_run_registry import (
    build_run_record, append_registry_record, generate_run_id,
    evaluate_gate,
)

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "strategies")

SAFETY_FLAGS = [
    "PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET", "NO_ENV_READ",
    "NO_ACCOUNT", "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
    "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT", "NO_WEBHOOK_SEND",
    "UPDATE_ONLY_PIPELINE", "NO_NEW_POSITIONS",
]


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _run_step(step_name: str, cmd: list[str]) -> dict:
    started = _ts()
    t0 = datetime.now()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        exit_code = proc.returncode
        stdout_tail = "\n".join(proc.stdout.strip().splitlines()[-10:])
        stderr_tail = "\n".join(proc.stderr.strip().splitlines()[-5:])
        status = "PASS" if exit_code == 0 else "FAIL"
    except subprocess.TimeoutExpired:
        exit_code, stdout_tail, stderr_tail, status = -1, "", "TIMEOUT after 300s", "FAIL"
    except Exception as e:
        exit_code, stdout_tail, stderr_tail, status = -1, "", str(e), "FAIL"

    finished = _ts()
    duration = (datetime.now() - t0).total_seconds()
    return {
        "step_name": step_name,
        "command": cmd,
        "started_at": started,
        "finished_at": finished,
        "duration_seconds": round(duration, 2),
        "exit_code": exit_code,
        "status": status,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }


def _extract_summary(date_str: str, output_dir: str) -> tuple[dict, list[str]]:
    summary: dict = {}
    missing: list[str] = []

    # Paper position summary
    pp_path = os.path.join(output_dir, f"{date_str}_paper_position_summary.json")
    if os.path.isfile(pp_path):
        with open(pp_path) as f:
            pp = json.load(f)
        lc = pp.get("lifecycle_stats", {})
        sc = pp.get("status_counts", {})
        summary["paper_position_count"] = sum(sc.values())
        summary["new_positions_count"] = lc.get("new_positions_count", 0)
        summary["existing_positions_count"] = lc.get("existing_positions_count", 0)
        summary["positions_updated_count"] = lc.get("positions_updated_count", 0)
        summary["positions_skipped_no_future_bars"] = lc.get("positions_skipped_no_future_bars", 0)
        summary["open_count"] = sc.get("OPEN", 0)
        summary["tp_count"] = sc.get("TAKE_PROFIT_HIT", 0)
        summary["sl_count"] = sc.get("STOP_LOSS_HIT", 0)
        summary["timeout_count"] = sc.get("TIMEOUT_EXIT", 0)
    else:
        missing.append("paper_position_summary")

    # Quarantine
    q_path = os.path.join(output_dir, f"{date_str}_paper_positions_quarantine.json")
    if os.path.isfile(q_path):
        with open(q_path) as f:
            q = json.load(f)
        summary["quarantined_count"] = q.get("quarantined_count", 0)
        summary["clean_count"] = q.get("clean_count", 0)
    else:
        missing.append("quarantine")

    # Scorecard
    sc_path = os.path.join(output_dir, f"{date_str}_paper_performance_scorecard.json")
    if os.path.isfile(sc_path):
        with open(sc_path) as f:
            sc_data = json.load(f)
        gm = sc_data.get("global_metrics", {})
        summary["closed_clean_positions"] = gm.get("closed_positions", 0)
        summary["sample_status"] = gm.get("sample_status", "UNKNOWN")
        summary["strategy_scorecard_rows"] = len(sc_data.get("strategy_scorecards", []))
    else:
        missing.append("scorecard")

    return summary, missing


def _build_steps(date_str: str, output_dir: str, allow_public_http: bool) -> list[dict]:
    py = sys.executable

    # Step 1: update existing positions only
    cmd1 = [
        py, os.path.join(SCRIPTS_DIR, "run_paper_position_simulator.py"),
        "--date", date_str,
        "--output-dir", output_dir,
        "--future-only",
        "--update-existing-only",
    ]
    if allow_public_http:
        cmd1.extend(["--allow-public-http", "--update-with-klines"])

    # Step 2: quarantine
    cmd2 = [
        py, os.path.join(SCRIPTS_DIR, "run_paper_position_quarantine.py"),
        "--date", date_str,
        "--output-dir", output_dir,
    ]

    # Step 3: scorecard
    cmd3 = [
        py, os.path.join(SCRIPTS_DIR, "run_paper_performance_scorecard.py"),
        "--date", date_str,
        "--output-dir", output_dir,
    ]

    # Step 4: sample gate
    cmd4 = [
        py, os.path.join(SCRIPTS_DIR, "run_sample_collection_gate.py"),
        "--date", date_str,
        "--registry-dir", output_dir,
        "--output-dir", output_dir,
    ]

    return [
        {"name": "run_paper_position_simulator_update_only", "cmd": cmd1},
        {"name": "run_paper_position_quarantine", "cmd": cmd2},
        {"name": "run_paper_performance_scorecard", "cmd": cmd3},
        {"name": "run_sample_collection_gate", "cmd": cmd4},
    ]


def render_markdown(result: dict) -> str:
    summary = result.get("summary", {})
    steps = result.get("steps", [])
    lines = [
        "# Shadow Position Update-Only Pipeline",
        "",
        f"**Date:** {result.get('date', '')}",
        f"**Mode:** {result.get('mode', '')}",
        f"**Pipeline status:** {result.get('pipeline_status', '')}",
        "",
        "## Summary",
        "",
        "影子持仓只更新流程",
        "",
        "说明：",
        "本流程只更新已有 OPEN paper positions。",
        "不扫描新策略。",
        "不生成新 TradeIntent。",
        "不新增 paper position。",
        "不下单，不 testnet/live。",
        "",
        "当前结果：",
        f"- existing positions: {summary.get('existing_positions_count', 'N/A')}",
        f"- positions updated: {summary.get('positions_updated_count', 'N/A')}",
        f"- skipped (no future bars): {summary.get('positions_skipped_no_future_bars', 'N/A')}",
        f"- new positions: {summary.get('new_positions_count', 0)} (should always be 0)",
        f"- clean positions: {summary.get('clean_count', 'N/A')}",
        f"- closed clean positions: {summary.get('closed_clean_positions', 'N/A')}",
        f"- sample_status: {summary.get('sample_status', 'N/A')}",
        "",
    ]

    ss = summary.get("sample_status", "")
    if ss in ("INSUFFICIENT_CLOSED_SAMPLE", "LOW_SAMPLE_SIZE"):
        lines.extend([
            "结论：",
            f"sample_status={ss}，不允许进入 testnet/live。",
            "继续 shadow 收集。",
            "",
        ])

    # Step Results
    lines.extend(["## Step Results", ""])
    lines.append("| Step | Status | Duration | Exit |")
    lines.append("|------|--------|----------|------|")
    for step in steps:
        lines.append(
            f"| {step['step_name']} | {step['status']} "
            f"| {step['duration_seconds']}s | {step['exit_code']} |"
        )
    lines.append("")
    passed = sum(1 for s in steps if s["status"] == "PASS")
    lines.append(f"Steps passed: {passed}/{len(steps)}")
    lines.append("")

    # Position Update
    lines.extend(["## Position Update", ""])
    for key in [
        "existing_positions_count", "positions_updated_count",
        "positions_skipped_no_future_bars", "new_positions_count",
    ]:
        lines.append(f"- {key}: {summary.get(key, 'N/A')}")
    lines.append("")

    # Scorecard
    lines.extend(["## Scorecard", ""])
    lines.append(f"- closed_clean_positions: {summary.get('closed_clean_positions', 'N/A')}")
    lines.append(f"- sample_status: {summary.get('sample_status', 'N/A')}")
    lines.append(f"- strategy_scorecard_rows: {summary.get('strategy_scorecard_rows', 'N/A')}")
    lines.append("")

    # Sample Gate
    gate_status = result.get("sample_gate_status", "")
    if gate_status:
        lines.extend(["## Sample Gate", ""])
        lines.append(f"- testnet_gate_status: {gate_status}")
        lines.append("")

    # Safety
    lines.extend([
        "## Safety",
        "",
        "- Paper-only: YES",
        "- Shadow-only: YES",
        "- No new positions: YES",
        "- No strategy scan: YES",
        "- No trade intent generation: YES",
        "- No order: YES",
        "- No account: YES",
        "- No testnet/live: YES",
        "- No secret: YES",
        "",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 10L shadow position update-only pipeline",
    )
    parser.add_argument("--date", type=str, default=None)
    parser.add_argument("--allow-public-http", action="store_true", default=False)
    parser.add_argument("--stop-on-failure", action="store_true", default=True)
    parser.add_argument("--output-dir", type=str, default=REPORT_DIR)
    args = parser.parse_args()

    date_str = args.date or _today_str()
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    mode = "real_public_readonly" if args.allow_public_http else "offline"
    print(f"Shadow Position Update-Only Pipeline")
    print(f"Date: {date_str}")
    print(f"Mode: {mode}")
    print(f"Output: {output_dir}")
    print()

    step_defs = _build_steps(date_str, output_dir, args.allow_public_http)
    step_results = []
    pipeline_status = "PASS"

    for step_def in step_defs:
        name = step_def["name"]
        cmd = step_def["cmd"]
        print(f"=== Step: {name} ===")
        print(f"  cmd: {' '.join(cmd)}")

        result = _run_step(name, cmd)
        step_results.append(result)

        print(f"  status: {result['status']} (exit={result['exit_code']}, {result['duration_seconds']}s)")
        if result["stdout_tail"]:
            for line in result["stdout_tail"].splitlines()[-3:]:
                print(f"  | {line}")
        if result["status"] == "FAIL":
            pipeline_status = "FAIL"
            if result["stderr_tail"]:
                print(f"  ERR: {result['stderr_tail'][:200]}")
            if args.stop_on_failure:
                print(f"  STOP_ON_FAILURE: halting pipeline")
                break
        print()

    summary, missing_fields = _extract_summary(date_str, output_dir)

    # Evaluate gate
    closed = summary.get("closed_clean_positions", 0)
    sample_status = summary.get("sample_status", "UNKNOWN")
    gate_status, gate_reasons = evaluate_gate(closed, sample_status)

    run_id = generate_run_id()
    pipeline_result = {
        "date": date_str,
        "mode": mode,
        "pipeline_type": "update_only",
        "allow_public_http": args.allow_public_http,
        "pipeline_status": pipeline_status,
        "steps": step_results,
        "summary": summary,
        "missing_output_fields": missing_fields,
        "safety_flags": SAFETY_FLAGS,
        "run_id": run_id,
        "sample_gate_status": gate_status,
        "sample_gate_reasons": gate_reasons,
    }

    # Registry (best-effort)
    registry_written = False
    try:
        record = build_run_record(pipeline_result, run_id=run_id)
        append_registry_record(record, output_dir)
        registry_written = True
    except Exception as e:
        print(f"WARNING: registry write failed: {e}")

    pipeline_result["registry_written"] = registry_written

    # Write outputs
    json_path = os.path.join(output_dir, f"{date_str}_shadow_position_update_result.json")
    with open(json_path, "w") as f:
        json.dump(pipeline_result, f, indent=2)
    print(f"Update result JSON: {json_path}")

    md_path = os.path.join(output_dir, f"{date_str}_shadow_position_update_result.md")
    with open(md_path, "w") as f:
        f.write(render_markdown(pipeline_result))
    print(f"Update result Markdown: {md_path}")

    passed = sum(1 for s in step_results if s["status"] == "PASS")
    print(f"\n=== Update-Only Pipeline Complete ===")
    print(f"Pipeline status: {pipeline_status}")
    print(f"Steps: {passed}/{len(step_results)} passed")
    for key, val in summary.items():
        print(f"  {key}: {val}")
    print(f"  gate: {gate_status}")
    if missing_fields:
        print(f"  missing: {missing_fields}")

    return 0 if pipeline_status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
