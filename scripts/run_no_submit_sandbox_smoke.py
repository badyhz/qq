#!/usr/bin/env python3
"""Wave 7: No-submit sandbox smoke simulation."""
import json, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_sandbox.no_submit_sandbox_smoke import run_smoke, write_smoke_result, write_simulated_records, render_smoke_report

    # Load latest signals if available
    signals_path = ROOT / "data" / "runtime" / "shadow" / "signals.jsonl"
    signals = []
    if signals_path.exists():
        for line in signals_path.read_text(encoding="utf-8").strip().splitlines():
            if line.strip():
                try:
                    signals.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    result = run_smoke(signals)
    write_smoke_result(result, ROOT / "data" / "runtime" / "testnet_sandbox" / "no_submit_sandbox_smoke.json")

    # Generate simulated records
    records = []
    for s in result.steps:
        if s.step == "simulated_adapter":
            for i in range(3):
                records.append({"record_id": f"SIM_REC_{i:04d}", "simulated": True, "real_submit": False, "testnet_submit": False, "no_submit_enforced": True, "status": "SIMULATED_NEW"})
    write_simulated_records(records, ROOT / "data" / "runtime" / "testnet_sandbox" / "simulated_submit_records.jsonl")
    (ROOT / "reports" / "no_submit_sandbox_smoke_report.md").write_text(render_smoke_report(result), encoding="utf-8")

    ok = result.overall == "NO_SUBMIT_SANDBOX_SMOKE_PASS" and result.no_real_submit and result.no_testnet_submit
    print(f"No-submit sandbox smoke: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
