#!/usr/bin/env python3
"""Wave 1: Exchange sandbox dry-run harness."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_final_gate.exchange_dry_run_harness import run_harness, write_result, render_report
    result = run_harness()
    write_result(result, ROOT / "data" / "runtime" / "testnet_final_gate" / "exchange_dry_run_harness.json")
    (ROOT / "reports" / "exchange_sandbox_dry_run_harness_report.md").write_text(render_report(result), encoding="utf-8")
    ok = result.no_network and result.no_real_key and result.no_submit
    print(f"Exchange dry-run harness: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
