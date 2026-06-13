"""Runner: real credential vault requirement checklist."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "credential_vault_reqs"
REPORT_DIR = ROOT / "reports" / "credential_vault_reqs"

def main() -> int:
    reqs_mod = importlib.import_module("src.runtime_integrations.testnet_enablement.credential_vault_requirements")

    requirements = reqs_mod.get_requirements()
    reqs_mod.write_requirements(requirements, OUT_DIR / "credential_vault_requirements.json")
    report = reqs_mod.render_report(requirements)
    (REPORT_DIR / "credential_vault_requirements.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "credential_vault_requirements.md").write_text(report, encoding="utf-8")

    print(f"credential_vault_requirements: {len(requirements)} requirements")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
