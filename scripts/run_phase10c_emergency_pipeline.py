"""Phase 10C-3L emergency one-click pipeline — chains watchlist → recheck → preview → payload → send gate dry-run.

Default: offline sample, no real HTTP, no Feishu send, no secrets, no orders.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "phase10c", "emergency")

DEFAULT_SYMBOLS = [
    "BNBUSDT", "DOGEUSDT", "AVAXUSDT", "SUIUSDT", "ARBUSDT",
    "TIAUSDT", "APTUSDT", "1000PEPEUSDT", "XRPUSDT",
]
DEFAULT_TIMEFRAMES = ["5m", "15m", "1h"]
DEFAULT_LIMIT = 120

SAFETY_FLAGS = [
    "PAPER_ONLY", "PUBLIC_READONLY_ONLY", "NO_SECRET", "NO_ENV_READ",
    "NO_ACCOUNT", "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
    "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT", "NO_WEBHOOK_SEND",
    "PIPELINE_DRY_RUN_ONLY",
]


# Chinese direction labels
DIRECTION_CN = {
    "LONG_OBSERVE": "多头观察",
    "SHORT_OBSERVE": "空头观察",
    "NO_TRADE": "不交易",
}


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _run_step(step_name: str, cmd: list[str]) -> tuple[int, str]:
    """Run a pipeline step and return (returncode, output)."""
    print(f"\n{'='*60}")
    print(f"STEP: {step_name}")
    print(f"CMD: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=REPO_ROOT,
        )
        output = result.stdout + result.stderr
        print(output)
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return 1, f"TIMEOUT after 300s"
    except Exception as e:
        return 1, str(e)


def _generate_human_summary(plans: list[dict]) -> dict[str, Any]:
    """Generate human-readable summary from focused plans."""
    watch_now = []
    wait_confirmation = []
    short_observe = []
    avoid = []

    for p in plans:
        symbol = p.get("symbol", "")
        tf = p.get("timeframe", "")
        direction = p.get("direction", "NO_TRADE")
        direction_cn = DIRECTION_CN.get(direction, direction)
        decision = p.get("plan_decision", "AVOID")
        reason = p.get("reason", "")

        entry = {"symbol": symbol, "tf": tf, "direction": direction_cn, "reason": reason}

        if decision == "WATCH":
            if direction == "SHORT_OBSERVE":
                short_observe.append(entry)
            else:
                watch_now.append(entry)
        elif decision == "WAIT":
            wait_confirmation.append(entry)
        else:
            avoid.append(entry)

    # Build watch now summary
    watch_lines = []
    for w in watch_now:
        reason_cn = _reason_short(w["reason"], w["direction"])
        watch_lines.append(f"- {w['symbol']} {w['tf']}：{reason_cn}")

    # Build wait summary
    wait_symbols = sorted(set(w["symbol"] for w in wait_confirmation))
    wait_line = f"- {', '.join(wait_symbols)}：等待 1h MACD 进一步确认" if wait_symbols else "- 暂无"

    # Build short summary
    short_lines = []
    for s in short_observe:
        short_lines.append(f"- {s['symbol']} {s['tf']}：空头信号观察中")

    # Build human summary text
    lines = ["今日只读盯盘摘要", ""]
    if watch_lines:
        lines.append("1. 当前可观察：")
        lines.extend(watch_lines)
        lines.append("")
    if wait_line:
        lines.append("2. 继续等待：")
        lines.append(wait_line)
        lines.append("")
    if short_lines:
        lines.append("3. 弱势观察：")
        lines.extend(short_lines)
        lines.append("")
    lines.append("4. 安全边界：")
    lines.append("- 只读行情")
    lines.append("- paper-only")
    lines.append("- 不下单")
    lines.append("- 不 testnet/live")
    lines.append("- 飞书默认 dry-run")

    human_text = "\n".join(lines)

    return {
        "human_summary": human_text,
        "watch_now_summary": [f"{w['symbol']} {w['tf']}：{w['direction']}" for w in watch_now],
        "wait_confirmation_summary": wait_symbols,
        "short_observe_summary": [f"{s['symbol']} {s['tf']}：空头观察" for s in short_observe],
        "safety_summary": "只读行情 / paper-only / 不下单 / 不 testnet/live / 飞书默认 dry-run",
    }


def _reason_short(reason: str, direction: str) -> str:
    """Short Chinese reason for summary."""
    if not reason:
        return "信号分析完成"
    r = reason.lower()
    if "macd" in r and ("green" in r or "bullish" in r or "expanding" in r):
        return "短周期转强，纸面观察"
    if "macd" in r and ("red" in r or "bearish" in r):
        return "短周期偏弱"
    if "turning" in r or "near_turn" in r:
        return "即将转折，等待确认"
    if "short" in r:
        return "空头信号观察中"
    if "long" in r:
        return "多头信号增强"
    return "信号分析中"


from typing import Any


def run_pipeline(
    allow_public_http: bool = False,
    offline_sample: bool = False,
    symbols: list[str] | None = None,
    timeframes: list[str] | None = None,
    limit: int = DEFAULT_LIMIT,
    date_str: str | None = None,
) -> int:
    """Run the full emergency pipeline."""
    if symbols is None:
        symbols = DEFAULT_SYMBOLS
    if timeframes is None:
        timeframes = DEFAULT_TIMEFRAMES
    if date_str is None:
        date_str = _today_str()

    mode = "offline_sample" if offline_sample else "real_public_http"
    symbol_str = ",".join(symbols)
    tf_str = ",".join(timeframes)

    print(f"=== Phase 10C-3L Emergency One-Click Pipeline ===")
    print(f"Date: {date_str}")
    print(f"Mode: {mode}")
    print(f"Symbols: {symbol_str}")
    print(f"Timeframes: {tf_str}")
    print(f"Limit: {limit}")
    print(f"allow_public_http: {allow_public_http}")
    print(f"offline_sample: {offline_sample}")

    steps = []
    errors = []
    reports_generated = []

    # Build common args
    http_args = ["--allow-public-http"] if allow_public_http else []
    offline_args = ["--offline-sample"] if offline_sample else []
    base_args = http_args + offline_args + [
        "--symbols", symbol_str,
        "--timeframes", tf_str,
        "--limit", str(limit),
    ]

    # Step 1: Emergency Watchlist
    step1_cmd = [sys.executable, os.path.join("scripts", "run_phase10c_emergency_signal_report.py")] + base_args
    rc1, out1 = _run_step("Emergency Watchlist", step1_cmd)
    steps.append({"name": "emergency_watchlist", "returncode": rc1, "status": "PASS" if rc1 == 0 else "FAIL"})
    if rc1 != 0:
        errors.append({"step": "emergency_watchlist", "error": out1[:500]})
    reports_generated.extend([
        f"{date_str}_signal_report.json",
        f"{date_str}_signal_report.md",
        f"{date_str}_candidates.csv",
        f"{date_str}_actionable_watch.json",
        f"{date_str}_actionable_watch.md",
    ])

    # Step 2: Trigger Recheck
    step2_cmd = [sys.executable, os.path.join("scripts", "run_phase10c_trigger_recheck.py")] + base_args
    rc2, out2 = _run_step("Trigger Recheck", step2_cmd)
    steps.append({"name": "trigger_recheck", "returncode": rc2, "status": "PASS" if rc2 == 0 else "FAIL"})
    if rc2 != 0:
        errors.append({"step": "trigger_recheck", "error": out2[:500]})
    reports_generated.extend([
        f"{date_str}_trigger_recheck.json",
        f"{date_str}_trigger_recheck.md",
        f"{date_str}_trigger_recheck.csv",
    ])

    # Step 3: Focused Paper Plan Preview
    step3_cmd = [sys.executable, os.path.join("scripts", "run_phase10c_focused_paper_plan_preview.py")] + base_args
    rc3, out3 = _run_step("Focused Paper Plan Preview", step3_cmd)
    steps.append({"name": "focused_paper_plan_preview", "returncode": rc3, "status": "PASS" if rc3 == 0 else "FAIL"})
    if rc3 != 0:
        errors.append({"step": "focused_paper_plan_preview", "error": out3[:500]})
    reports_generated.extend([
        f"{date_str}_focused_paper_plan_preview.json",
        f"{date_str}_focused_paper_plan_preview.md",
        f"{date_str}_focused_paper_plan_preview.csv",
    ])

    # Step 4: Feishu Paper Alert Payload
    step4_cmd = [sys.executable, os.path.join("scripts", "run_phase10c_feishu_paper_alert_payload.py")]
    rc4, out4 = _run_step("Feishu Paper Alert Payload", step4_cmd)
    steps.append({"name": "feishu_paper_alert_payload", "returncode": rc4, "status": "PASS" if rc4 == 0 else "FAIL"})
    if rc4 != 0:
        errors.append({"step": "feishu_paper_alert_payload", "error": out4[:500]})
    reports_generated.extend([
        f"{date_str}_feishu_paper_alert_payload.json",
        f"{date_str}_feishu_paper_alert_payload.md",
    ])

    # Step 5: Feishu Send Gate Dry-run
    step5_cmd = [sys.executable, os.path.join("scripts", "run_phase10c_feishu_alert_send_gate.py"), "--dry-run"]
    rc5, out5 = _run_step("Feishu Send Gate Dry-run", step5_cmd)
    steps.append({"name": "feishu_send_gate_dry_run", "returncode": rc5, "status": "PASS" if rc5 == 0 else "FAIL"})
    if rc5 != 0:
        errors.append({"step": "feishu_send_gate_dry_run", "error": out5[:500]})
    reports_generated.extend([
        f"{date_str}_feishu_send_result.json",
        f"{date_str}_feishu_send_result.md",
    ])

    # Determine final status
    all_pass = all(s["returncode"] == 0 for s in steps)
    final_status = "PIPELINE_PASS" if all_pass else "PARTIAL_FAIL"

    # Read payload count from payload file
    payload_count = 0
    payload_file = os.path.join(REPORT_DIR, f"{date_str}_feishu_paper_alert_payload.json")
    if os.path.isfile(payload_file):
        try:
            with open(payload_file) as f:
                pdata = json.load(f)
                payload_count = pdata.get("payload_count", 0)
        except Exception:
            pass

    # Read focused plan preview for human summary
    preview_file = os.path.join(REPORT_DIR, f"{date_str}_focused_paper_plan_preview.json")
    plans = []
    if os.path.isfile(preview_file):
        try:
            with open(preview_file) as f:
                preview_data = json.load(f)
                plans = preview_data.get("plans", [])
        except Exception:
            pass

    # Generate human summary
    human_summary = _generate_human_summary(plans)

    # Write pipeline result
    os.makedirs(REPORT_DIR, exist_ok=True)

    result_data = {
        "date": date_str,
        "mode": mode,
        "allow_public_http": allow_public_http,
        "offline_sample": offline_sample,
        "symbols": symbols,
        "timeframes": timeframes,
        "limit": limit,
        "steps": steps,
        "step_status": {s["name"]: s["status"] for s in steps},
        "reports_generated": reports_generated,
        "payload_count": payload_count,
        "send_attempted": False,
        "actually_sent": False,
        "safety_flags": SAFETY_FLAGS,
        "final_status": final_status,
        "errors": errors,
        "human_summary": human_summary["human_summary"],
        "watch_now_summary": human_summary["watch_now_summary"],
        "wait_confirmation_summary": human_summary["wait_confirmation_summary"],
        "short_observe_summary": human_summary["short_observe_summary"],
        "safety_summary": human_summary["safety_summary"],
    }

    json_path = os.path.join(REPORT_DIR, f"{date_str}_emergency_pipeline_result.json")
    with open(json_path, "w") as f:
        json.dump(result_data, f, indent=2)
    print(f"\nPipeline JSON: {json_path}")

    md_path = os.path.join(REPORT_DIR, f"{date_str}_emergency_pipeline_result.md")
    with open(md_path, "w") as f:
        f.write(f"# 一键盯盘 Pipeline 结果 — {date_str}\n\n")
        f.write(f"## 摘要\n\n")
        f.write(f"- **模式:** {mode}\n")
        f.write(f"- **allow_public_http:** {allow_public_http}\n")
        f.write(f"- **offline_sample:** {offline_sample}\n")
        f.write(f"- **最终状态:** {final_status}\n")
        f.write(f"- **提醒数量:** {payload_count}\n")
        f.write(f"- **发送尝试:** 否\n")
        f.write(f"- **实际发送:** 否\n\n")

        f.write(f"## 今日只读盯盘摘要\n\n")
        f.write("```text\n")
        f.write(human_summary["human_summary"])
        f.write("\n```\n\n")

        f.write(f"## 步骤结果\n\n")
        f.write("| 步骤 | 状态 |\n|---|---|\n")
        for s in steps:
            f.write(f"| {s['name']} | {s['status']} |\n")

        if errors:
            f.write(f"\n## 错误\n\n")
            for err in errors:
                f.write(f"- **{err['step']}:** {err['error'][:200]}\n")

        f.write(f"\n## 生成的报告\n\n")
        for r in reports_generated:
            f.write(f"- `{r}`\n")

        f.write(f"\n## 提醒摘要\n\n")
        f.write(f"- **提醒数量:** {payload_count}\n")
        f.write(f"- **发送尝试:** 否\n")
        f.write(f"- **实际发送:** 否\n")

        f.write(f"\n## 飞书发送门禁\n\n")
        f.write("发送门禁以 dry-run 模式执行。\n")
        f.write("未提供 webhook URL，未真实发送。\n")

        f.write(f"\n## 安全边界\n\n")
        f.write("- 纸面观察，不下单\n")
        f.write("- 只读行情数据\n")
        f.write("- 不涉及账户、订单、testnet、live\n")
        f.write("- 不读取 websocket、secret、.env\n")
        f.write("- 不真实发送飞书\n")
        f.write("- 手动飞书发送保持独立\n")
    print(f"Pipeline Markdown: {md_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"PIPELINE RESULT: {final_status}")
    print(f"{'='*60}")
    for s in steps:
        print(f"  {s['name']}: {s['status']}")
    print(f"  payload_count: {payload_count}")
    print(f"  send_attempted: False")
    print(f"  actually_sent: False")

    return 0 if all_pass else 1


def main():
    parser = argparse.ArgumentParser(description="Phase 10C-3L emergency one-click pipeline")
    parser.add_argument("--allow-public-http", action="store_true")
    parser.add_argument("--offline-sample", action="store_true")
    parser.add_argument("--symbols", type=str, default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--timeframes", type=str, default=",".join(DEFAULT_TIMEFRAMES))
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--date", type=str, default=None)
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    timeframes = [t.strip() for t in args.timeframes.split(",") if t.strip()]

    # Default to offline if neither specified
    if not args.allow_public_http and not args.offline_sample:
        args.offline_sample = True

    return run_pipeline(
        allow_public_http=args.allow_public_http,
        offline_sample=args.offline_sample,
        symbols=symbols,
        timeframes=timeframes,
        limit=args.limit,
        date_str=args.date,
    )


if __name__ == "__main__":
    sys.exit(main())
