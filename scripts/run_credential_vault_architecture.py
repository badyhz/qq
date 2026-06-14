"""Runner: credential vault architecture."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_adapter_spec"
REPORT_DIR = ROOT / "reports" / "testnet_adapter_spec"

def main() -> int:
    arch_mod = importlib.import_module("src.runtime_integrations.testnet_adapter_spec.credential_vault_architecture")
    validator_mod = importlib.import_module("src.runtime_integrations.testnet_adapter_spec.credential_vault_architecture_validator")

    sections = arch_mod.get_sections()
    arch_mod.write_architecture(sections, OUT_DIR / "credential_vault_architecture.json")
    report = arch_mod.render_report(sections)
    (REPORT_DIR / "credential_vault_architecture.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "credential_vault_architecture.md").write_text(report, encoding="utf-8")

    checks = validator_mod.validate_architecture(report)
    validator_mod.write_checks(checks, OUT_DIR / "credential_vault_architecture_checks.json")

    passed = sum(1 for c in checks if c.passed)
    print(f"credential_vault_architecture: {len(sections)} sections, {passed}/{len(checks)} checks passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
