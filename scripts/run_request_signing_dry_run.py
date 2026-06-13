#!/usr/bin/env python3
"""Wave 3: Request signing dry-run."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_final_gate.request_signing_dry_run import run_signing_dry_run, write_result, render_report
    result = run_signing_dry_run("BTCUSDT", "BUY", 0.001)
    write_result(result, ROOT / "data" / "runtime" / "testnet_final_gate" / "request_signing_dry_run.json")
    (ROOT / "reports" / "request_signing_dry_run_report.md").write_text(render_report(result), encoding="utf-8")
    ok = (result.signing_mode == "DRY_RUN_ONLY" and result.fake_signature
          and result.signature_redacted and not result.real_secret_used and not result.request_sendable)
    print(f"Request signing: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
