#!/usr/bin/env python3
"""Wave 5: Sandbox risk control check."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_sandbox.sandbox_risk_controls import run_all_checks, write_checks
    from src.runtime_integrations.testnet_sandbox.sandbox_risk_report import render_risk_report

    checks = run_all_checks(
        symbol="BTCUSDT", quantity=0.001, price=50000.0, intent_id="INT_TEST",
        seen_intents=set(), approval_status="DENIED", kill_switch_blocking=True,
        daily_count=5, reference_price=50000.0, signal_ts="2026-06-14T00:00:00Z",
    )
    write_checks(checks, ROOT / "data" / "runtime" / "testnet_sandbox" / "sandbox_risk_control_check.json")
    (ROOT / "reports" / "sandbox_risk_control_report.md").write_text(render_risk_report(checks), encoding="utf-8")

    ok = all(c.passed for c in checks)
    print(f"Sandbox risk controls: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
