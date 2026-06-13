#!/usr/bin/env python3
"""Wave 3: Human approval gate check."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_sandbox.human_approval_gate import create_request, default_decision, deny_stale, deny_incomplete, write_gate_check, render_gate_report

    # Test default deny
    req = create_request("INT_001", "BTCUSDT", "BUY", 0.001)
    d1 = default_decision(req)
    d2 = deny_stale(req)
    d3 = deny_incomplete(req, ("price", "risk_summary"))
    decisions = [d1, d2, d3]

    write_gate_check(decisions, ROOT / "data" / "runtime" / "testnet_sandbox" / "human_approval_gate_check.json")
    (ROOT / "reports" / "human_approval_gate_report.md").write_text(render_gate_report(decisions), encoding="utf-8")

    ok = (
        all(not d.approved for d in decisions)
        and all(not d.submit_allowed for d in decisions)
        and all(d.human_approval_required for d in decisions)
    )
    print(f"Human approval gate: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
