"""Runner: exchange permission review checklist."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "exchange_permissions"
REPORT_DIR = ROOT / "reports" / "exchange_permissions"

def main() -> int:
    perms_mod = importlib.import_module("src.runtime_integrations.testnet_enablement.exchange_permission_review")

    permissions = perms_mod.get_permissions()
    perms_mod.write_permissions(permissions, OUT_DIR / "exchange_permissions.json")
    report = perms_mod.render_report(permissions)
    (REPORT_DIR / "exchange_permissions.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "exchange_permissions.md").write_text(report, encoding="utf-8")

    print(f"exchange_permissions: {len(permissions)} permissions")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
