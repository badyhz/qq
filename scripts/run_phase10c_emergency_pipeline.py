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
    }

    json_path = os.path.join(REPORT_DIR, f"{date_str}_emergency_pipeline_result.json")
    with open(json_path, "w") as f:
        json.dump(result_data, f, indent=2)
    print(f"\nPipeline JSON: {json_path}")

    md_path = os.path.join(REPORT_DIR, f"{date_str}_emergency_pipeline_result.md")
    with open(md_path, "w") as f:
        f.write(f"# Emergency One-Click Pipeline Result — {date_str}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- **Mode:** {mode}\n")
        f.write(f"- **allow_public_http:** {allow_public_http}\n")
        f.write(f"- **offline_sample:** {offline_sample}\n")
        f.write(f"- **Final Status:** {final_status}\n")
        f.write(f"- **Payload Count:** {payload_count}\n")
        f.write(f"- **Send Attempted:** False\n")
        f.write(f"- **Actually Sent:** False\n\n")

        f.write(f"## Step Results\n\n")
        f.write("| Step | Status |\n|---|---|\n")
        for s in steps:
            f.write(f"| {s['name']} | {s['status']} |\n")

        if errors:
            f.write(f"\n## Errors\n\n")
            for err in errors:
                f.write(f"- **{err['step']}:** {err['error'][:200]}\n")

        f.write(f"\n## Generated Reports\n\n")
        for r in reports_generated:
            f.write(f"- `{r}`\n")

        f.write(f"\n## Payload Summary\n\n")
        f.write(f"- **payload_count:** {payload_count}\n")
        f.write(f"- **send_attempted:** False\n")
        f.write(f"- **actually_sent:** False\n")

        f.write(f"\n## Feishu Send Gate Dry-run\n\n")
        f.write("Send gate executed in dry-run mode.\n")
        f.write("No webhook URL provided. No real send.\n")

        f.write(f"\n## Safety\n\n")
        f.write("- Paper-only observation pipeline\n")
        f.write("- Readonly-only market data\n")
        f.write("- No account, no order, no testnet, no live\n")
        f.write("- No websocket, no secret, no .env\n")
        f.write("- No real Feishu send\n")
        f.write("- Manual Feishu send remains separate\n")
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
