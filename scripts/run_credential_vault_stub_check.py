#!/usr/bin/env python3
"""Wave 2: Credential vault stub check."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_sandbox.credential_vault_stub import check_vault_stub, write_vault_check, render_vault_report, STUB_CREDENTIALS

    check = check_vault_stub()
    write_vault_check(check, ROOT / "data" / "runtime" / "testnet_sandbox" / "credential_vault_stub_check.json")
    (ROOT / "reports" / "credential_vault_stub_report.md").write_text(render_vault_report(check), encoding="utf-8")

    ok = (
        not check.real_credentials_loaded
        and not check.env_secret_read
        and check.vault_mode == "STUB_ONLY"
        and not check.submit_allowed
        and check.all_redacted
    )
    print(f"Credential vault stub: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
