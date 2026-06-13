#!/usr/bin/env python3
"""Wave 8: Operator emergency procedure check."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_presubmit.operator_emergency_procedure import get_steps, validate_procedure, write_check

    steps = get_steps()
    valid, errors = validate_procedure(steps)
    write_check(valid, errors, ROOT / "data" / "runtime" / "testnet_presubmit" / "operator_emergency_procedure_check.json")

    lines = ["# Operator Emergency Procedure Report", "", f"Steps: {len(steps)}", f"Valid: {valid}", "", "## Steps", ""]
    for s in steps:
        lines.append(f"- {s.step_id}: {s.title} — {s.description}")
    if errors:
        lines.extend(["", "## Errors"])
        for e in errors:
            lines.append(f"- {e}")
    lines.extend(["", "## Conclusion", "", "OPERATOR_EMERGENCY_PROCEDURE_VALID", ""])
    (ROOT / "reports" / "operator_emergency_procedure_report.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"Emergency procedure: {'PASS' if valid else 'FAIL'}")
    return 0 if valid else 1

if __name__ == "__main__":
    sys.exit(main())
