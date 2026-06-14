"""Runner: exchange permission isolation plan."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_adapter_spec"
REPORT_DIR = ROOT / "reports" / "testnet_adapter_spec"

def main() -> int:
    perm_mod = importlib.import_module("src.runtime_integrations.testnet_adapter_spec.exchange_permission_isolation")

    permissions = perm_mod.get_permissions()
    perm_mod.write_plan(permissions, OUT_DIR / "exchange_permission_isolation_plan.json")
    report = perm_mod.render_report(permissions)
    (REPORT_DIR / "exchange_permission_isolation_plan.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "exchange_permission_isolation_plan.md").write_text(report, encoding="utf-8")

    print(f"exchange_permission_isolation: {len(permissions)} permissions")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
