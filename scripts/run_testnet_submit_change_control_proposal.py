"""Runner: testnet submit change control proposal."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "change_control"
REPORT_DIR = ROOT / "reports" / "change_control"

def main() -> int:
    proposal_mod = importlib.import_module("src.runtime_integrations.testnet_enablement.change_control_proposal")
    validator_mod = importlib.import_module("src.runtime_integrations.testnet_enablement.change_control_validator")

    proposal = proposal_mod.create_proposal()
    proposal_mod.write_proposal(proposal, OUT_DIR / "change_control_proposal.json")
    report = proposal_mod.render_report(proposal)
    (REPORT_DIR / "change_control_proposal.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "change_control_proposal.md").write_text(report, encoding="utf-8")

    checks = validator_mod.validate_proposal(proposal.to_dict())
    validator_mod.write_checks(checks, OUT_DIR / "change_control_checks.json")
    validator_report = validator_mod.render_report(checks) if hasattr(validator_mod, "render_report") else ""
    if validator_report:
        (REPORT_DIR / "change_control_checks.md").write_text(validator_report, encoding="utf-8")

    passed = sum(1 for c in checks if c.passed)
    print(f"change_control_proposal: {proposal.proposal_id}")
    print(f"change_control_checks: {passed}/{len(checks)} passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
