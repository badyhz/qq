"""Runner: external testnet adapter design spec."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_adapter_spec"
REPORT_DIR = ROOT / "reports" / "testnet_adapter_spec"

def main() -> int:
    spec_mod = importlib.import_module("src.runtime_integrations.testnet_adapter_spec.external_adapter_spec")
    validator_mod = importlib.import_module("src.runtime_integrations.testnet_adapter_spec.external_adapter_spec_validator")

    sections = spec_mod.get_sections()
    spec_mod.write_spec(sections, OUT_DIR / "external_adapter_spec.json")
    report = spec_mod.render_report(sections)
    (REPORT_DIR / "external_adapter_spec.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "external_adapter_spec.md").write_text(report, encoding="utf-8")

    checks = validator_mod.validate_spec(sections)
    validator_mod.write_checks(checks, OUT_DIR / "external_adapter_spec_checks.json")

    passed = sum(1 for c in checks if c.passed)
    print(f"external_adapter_spec: {len(sections)} sections, {passed}/{len(checks)} checks passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
