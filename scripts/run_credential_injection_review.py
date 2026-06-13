#!/usr/bin/env python3
"""Wave 2: Credential injection review."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_final_gate.credential_injection_review import run_review, write_review, render_report
    review = run_review()
    write_review(review, ROOT / "data" / "runtime" / "testnet_final_gate" / "credential_injection_review.json")
    (ROOT / "reports" / "credential_injection_review_report.md").write_text(render_report(review), encoding="utf-8")
    ok = (review.credential_source == "STUB_ONLY" and not review.env_secret_read
          and not review.credential_injection_allowed and not review.submit_allowed)
    print(f"Credential injection: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
