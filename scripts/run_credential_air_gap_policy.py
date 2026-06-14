"""Runner: credential air-gap policy."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_release_gate"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_release_gate"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_release_gate.credential_air_gap_policy")
    policy = mod.create_policy()
    mod.write_policy(policy, OUT_DIR / "credential_air_gap_policy.json")
    report = mod.render_report(policy)
    (REPORT_DIR / "credential_air_gap_policy_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "credential_air_gap_policy_report.md").write_text(report, encoding="utf-8")
    print(f"credential_air_gap_policy: {len(policy.rules)} rules")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
