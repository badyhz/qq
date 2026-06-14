"""Runner: vault stub contract."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_transport"
REPORT_DIR = ROOT / "reports" / "testnet_mock_transport"

def main() -> int:
    vault_mod = importlib.import_module("src.runtime_integrations.testnet_mock_transport.vault_stub_contract")
    validator_mod = importlib.import_module("src.runtime_integrations.testnet_mock_transport.vault_stub_validator")

    state = vault_mod.create_stub_state()
    vault_mod.write_stub(state, OUT_DIR / "vault_stub_contract.json")
    report = vault_mod.render_report(state)
    (REPORT_DIR / "vault_stub_contract.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "vault_stub_contract.md").write_text(report, encoding="utf-8")

    checks = validator_mod.validate_vault_stub(report)
    validator_mod.write_checks(checks, OUT_DIR / "vault_stub_contract_checks.json")

    passed = sum(1 for c in checks if c.passed)
    print(f"vault_stub_contract: {len(state.credential_references)} refs, {passed}/{len(checks)} checks passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
