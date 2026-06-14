"""Runner: threat model security review."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_adapter_spec"
REPORT_DIR = ROOT / "reports" / "testnet_adapter_spec"

def main() -> int:
    threat_mod = importlib.import_module("src.runtime_integrations.testnet_adapter_spec.threat_model_security_review")

    threats = threat_mod.get_threats()
    threat_mod.write_threats(threats, OUT_DIR / "threat_model_security_review.json")
    report = threat_mod.render_report(threats)
    (REPORT_DIR / "threat_model_security_review.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "threat_model_security_review.md").write_text(report, encoding="utf-8")

    print(f"threat_model_security_review: {len(threats)} threats documented")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
