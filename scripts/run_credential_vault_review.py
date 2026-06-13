#!/usr/bin/env python3
"""Wave 1: Credential vault review."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_presubmit.credential_review import run_credential_review, write_review, render_review_report
    from src.runtime_integrations.testnet_presubmit.credential_schema import get_schemas

    schemas = get_schemas()
    result = run_credential_review(len(schemas))
    write_review(result, ROOT / "data" / "runtime" / "testnet_presubmit" / "credential_review.json")
    (ROOT / "reports" / "credential_vault_review_report.md").write_text(render_review_report(result), encoding="utf-8")

    ok = not result.real_credentials_loaded and result.credential_mode == "REVIEW_STUB_ONLY" and not result.env_secret_read and not result.file_secret_read and not result.submit_allowed
    print(f"Credential vault review: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
