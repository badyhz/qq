"""Runner: request signing architecture."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_adapter_spec"
REPORT_DIR = ROOT / "reports" / "testnet_adapter_spec"

def main() -> int:
    arch_mod = importlib.import_module("src.runtime_integrations.testnet_adapter_spec.request_signing_architecture")
    validator_mod = importlib.import_module("src.runtime_integrations.testnet_adapter_spec.request_signing_validator")

    sections = arch_mod.get_sections()
    arch_mod.write_architecture(sections, OUT_DIR / "request_signing_architecture.json")
    report = arch_mod.render_report(sections)
    (REPORT_DIR / "request_signing_architecture.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "request_signing_architecture.md").write_text(report, encoding="utf-8")

    checks = validator_mod.validate_architecture(report)
    validator_mod.write_checks(checks, OUT_DIR / "request_signing_architecture_checks.json")

    passed = sum(1 for c in checks if c.passed)
    print(f"request_signing_architecture: {len(sections)} sections, {passed}/{len(checks)} checks passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
