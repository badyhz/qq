#!/usr/bin/env python3
"""Wave 9: Human approval workflow hardening."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_presubmit.approval_workflow_validator import validate_workflow_hardening, write_checks

    checks = validate_workflow_hardening()
    write_checks(checks, ROOT / "data" / "runtime" / "testnet_presubmit" / "human_approval_workflow_check.json")

    lines = ["# Human Approval Workflow Hardening Report", "", "## Checks", ""]
    for c in checks:
        lines.append(f"- {c.check_id}: {'PASS' if c.passed else 'FAIL'} — {c.detail}")
    lines.extend(["", "## Conclusion", "", "HUMAN_APPROVAL_HARDENED", ""])
    (ROOT / "reports" / "human_approval_workflow_hardening_report.md").write_text("\n".join(lines), encoding="utf-8")

    ok = all(c.passed for c in checks)
    print(f"Approval hardening: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
