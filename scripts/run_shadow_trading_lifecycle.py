"""Phase 10I Shadow Trading Lifecycle Pipeline.

One-command orchestrator for the shadow trading lifecycle:
  1. Enabled strategies runner
  2. Trade intent runner
  3. Paper position simulator (future-only update)
  4. Legacy quarantine
  5. Clean performance scorecard

No orders, no accounts, no secrets, no testnet, no live.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "strategies")

SAFETY_FLAGS = [
    "PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET", "NO_ENV_READ",
    "NO_ACCOUNT", "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
    "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT", "NO_WEBHOOK_SEND",
    "SHADOW_LIFECYCLE_PIPELINE",
]


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _run_step(
    step_name: str,
    cmd: list[str],
    stop_on_failure: bool = True,
) -> dict:
    started = _ts()
    t0 = datetime.now()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        exit_code = proc.returncode
        stdout_tail = "\n".join(proc.stdout.strip().splitlines()[-10:])
        stderr_tail = "\n".join(proc.stderr.strip().splitlines()[-5:])
        status = "PASS" if exit_code == 0 else "FAIL"
    except subprocess.TimeoutExpired:
        exit_code = -1
        stdout_tail = ""
        stderr_tail = "TIMEOUT after 300s"
        status = "FAIL"
    except Exception as e:
        exit_code = -1
        stdout_tail = ""
        stderr_tail = str(e)
        status = "FAIL"

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

    # Strategy run summary
    sr_path = os.path.join(output_dir, f"{date_str}_strategy_run_summary.json")
    if os.path.isfile(sr_path):
        with open(sr_path) as f:
            sr = json.load(f)
        summary["strategy_candidates_count"] = sr.get("candidate_count", 0)
    else:
        missing.append("strategy_run_summary")

    # Trade intents
    ti_path = os.path.join(output_dir, f"{date_str}_trade_intents.json")
    if os.path.isfile(ti_path):
        with open(ti_path) as f:
            ti = json.load(f)
        summary["trade_intents_count"] = ti.get("intent_count", 0)
        sc = ti.get("status_counts", {})
        summary["shadow_ready_count"] = sc.get("SHADOW_READY", 0)
    else:
        missing.append("trade_intents")

    # Paper positions
    pp_path = os.path.join(output_dir, f"{date_str}_paper_position_summary.json")
    if os.path.isfile(pp_path):
        with open(pp_path) as f:
            pp = json.load(f)
        sc = pp.get("status_counts", {})
        summary["paper_position_count"] = sum(sc.values())
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


def _build_steps(
    date_str: str,
    output_dir: str,
    allow_public_http: bool,
    offline_sample: bool,
) -> list[dict]:
    py = sys.executable

    # Step 1: enabled strategies
    cmd1 = [
        py, os.path.join(SCRIPTS_DIR, "run_enabled_strategies.py"),
        "--date", date_str,
    ]
    if allow_public_http:
        cmd1.append("--allow-public-http")
    if offline_sample:
        cmd1.append("--offline-sample")

    # Step 2: trade intents
    cmd2 = [
        py, os.path.join(SCRIPTS_DIR, "run_strategy_trade_intents.py"),
        "--date", date_str,
        "--output-dir", output_dir,
    ]

    # Step 3: paper position simulator
    cmd3 = [
        py, os.path.join(SCRIPTS_DIR, "run_paper_position_simulator.py"),
        "--date", date_str,
        "--output-dir", output_dir,
        "--future-only",
    ]
    if allow_public_http:
        cmd3.extend(["--allow-public-http", "--update-with-klines"])

    # Step 4: quarantine
    cmd4 = [
        py, os.path.join(SCRIPTS_DIR, "run_paper_position_quarantine.py"),
        "--date", date_str,
        "--output-dir", output_dir,
    ]

    # Step 5: scorecard
    cmd5 = [
        py, os.path.join(SCRIPTS_DIR, "run_paper_performance_scorecard.py"),
        "--date", date_str,
        "--output-dir", output_dir,
    ]

    return [
        {"name": "run_enabled_strategies", "cmd": cmd1},
        {"name": "run_strategy_trade_intents", "cmd": cmd2},
        {"name": "run_paper_position_simulator", "cmd": cmd3},
        {"name": "run_paper_position_quarantine", "cmd": cmd4},
        {"name": "run_paper_performance_scorecard", "cmd": cmd5},
    ]


def render_markdown(result: dict) -> str:
    summary = result.get("summary", {})
    steps = result.get("steps", [])
    lines = [
        "# Shadow Trading Lifecycle Pipeline",
        "",
        f"**Date:** {result.get('date', '')}",
        f"**Mode:** {result.get('mode', '')}",
        f"**Pipeline status:** {result.get('pipeline_status', '')}",
        "",
        "## Summary",
        "",
        "影子交易生命周期总入口",
        "",
        "状态：shadow-only",
        "不会下单",
        "不会连接账户",
        "不会 testnet/live",
        "",
        "当前结果：",
        f"- 策略候选：{summary.get('strategy_candidates_count', 'N/A')}",
        f"- TradeIntent：{summary.get('trade_intents_count', 'N/A')} (shadow_ready: {summary.get('shadow_ready_count', 'N/A')})",
        f"- PaperPosition：{summary.get('paper_position_count', 'N/A')}",
        f"- Clean positions：{summary.get('clean_count', 'N/A')}",
        f"- Closed clean positions：{summary.get('closed_clean_positions', 'N/A')}",
        f"- sample_status：{summary.get('sample_status', 'N/A')}",
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
    elif ss == "EVALUABLE":
        lines.extend([
            "结论：",
            "样本可评估，详见策略评分。",
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

    # Current Paper State
    lines.extend(["## Current Paper State", ""])
    for key in [
        "paper_position_count", "open_count", "tp_count", "sl_count", "timeout_count",
        "quarantined_count", "clean_count", "closed_clean_positions",
    ]:
        lines.append(f"- {key}: {summary.get(key, 'N/A')}")
    lines.append("")

    # Scorecard Status
    lines.extend(["## Scorecard Status", ""])
    lines.append(f"- sample_status: {summary.get('sample_status', 'N/A')}")
    lines.append(f"- strategy_scorecard_rows: {summary.get('strategy_scorecard_rows', 'N/A')}")
    lines.append("")

    # Safety
    lines.extend([
        "## Safety",
        "",
        "- Paper-only: YES",
        "- Shadow-only: YES",
        "- No order: YES",
        "- No account: YES",
        "- No testnet/live: YES",
        "- No secret: YES",
        "- No real execution: YES",
        "",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 10I shadow trading lifecycle pipeline",
    )
    parser.add_argument("--date", type=str, default=None)
    parser.add_argument("--allow-public-http", action="store_true", default=False)
    parser.add_argument("--offline-sample", action="store_true", default=False)
    parser.add_argument("--stop-on-failure", action="store_true", default=True)
    parser.add_argument("--output-dir", type=str, default=REPORT_DIR)
    args = parser.parse_args()

    date_str = args.date or _today_str()
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    mode = "real_public_readonly" if args.allow_public_http else "offline_sample"
    print(f"Shadow Trading Lifecycle Pipeline")
    print(f"Date: {date_str}")
    print(f"Mode: {mode}")
    print(f"Output: {output_dir}")
    print()

    step_defs = _build_steps(date_str, output_dir, args.allow_public_http, args.offline_sample)
    step_results = []
    pipeline_status = "PASS"

    for step_def in step_defs:
        name = step_def["name"]
        cmd = step_def["cmd"]
        print(f"=== Step: {name} ===")
        print(f"  cmd: {' '.join(cmd)}")

        result = _run_step(name, cmd, stop_on_failure=args.stop_on_failure)
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

    # Extract summary
    summary, missing_fields = _extract_summary(date_str, output_dir)

    # Build result
    pipeline_result = {
        "date": date_str,
        "mode": mode,
        "allow_public_http": args.allow_public_http,
        "pipeline_status": pipeline_status,
        "steps": step_results,
        "summary": summary,
        "missing_output_fields": missing_fields,
        "safety_flags": SAFETY_FLAGS,
    }

    # Write JSON
    json_path = os.path.join(output_dir, f"{date_str}_shadow_lifecycle_result.json")
    with open(json_path, "w") as f:
        json.dump(pipeline_result, f, indent=2)
    print(f"Lifecycle JSON: {json_path}")

    # Write Markdown
    md_path = os.path.join(output_dir, f"{date_str}_shadow_lifecycle_result.md")
    with open(md_path, "w") as f:
        f.write(render_markdown(pipeline_result))
    print(f"Lifecycle Markdown: {md_path}")

    # Final summary
    passed = sum(1 for s in step_results if s["status"] == "PASS")
    print(f"\n=== Shadow Lifecycle Pipeline Complete ===")
    print(f"Pipeline status: {pipeline_status}")
    print(f"Steps: {passed}/{len(step_results)} passed")
    for key, val in summary.items():
        print(f"  {key}: {val}")
    if missing_fields:
        print(f"  missing: {missing_fields}")

    return 0 if pipeline_status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
