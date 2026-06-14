"""Runner: credential policy stub."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_discovery"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_discovery"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_discovery.credential_policy_stub")
    policy = mod.create_policy()
    validation = mod.validate_policy(policy)
    mod.write_policy(policy, OUT_DIR / "credential_policy_stub.json")
    report = mod.render_report(policy)
    (REPORT_DIR / "credential_policy_stub_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "credential_policy_stub_report.md").write_text(report, encoding="utf-8")
    print(f"credential_policy_stub: class={policy.credential_class}, valid={validation[0]['valid']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
