"""Runner: de facto spec registry."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_scope_audit"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_scope_audit"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_scope_audit.de_facto_spec_registry")
    registry = mod.create_registry()
    mod.write_registry(registry, OUT_DIR / "de_facto_spec_registry.json")
    report = mod.render_report(registry)
    (REPORT_DIR / "de_facto_spec_registry_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "de_facto_spec_registry_report.md").write_text(report, encoding="utf-8")
    print(f"de_facto_spec_registry: {len(registry.entries)} entries documented")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
