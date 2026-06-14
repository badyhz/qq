"""Runner: no-network preflight evidence."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_preapproval"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_preapproval"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_preapproval.no_network_preflight_evidence")
    evidence = mod.create_evidence()
    mod.write_evidence(evidence, OUT_DIR / "no_network_preflight_evidence.json")
    report = mod.render_report(evidence)
    (REPORT_DIR / "no_network_preflight_evidence_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "no_network_preflight_evidence_report.md").write_text(report, encoding="utf-8")
    print(f"no_network_preflight_evidence: {mod.count_passed(evidence)}/{len(evidence.items)} passed, {mod.count_active_blockers(evidence)} active blockers")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
