"""Runner: unlock request dry-run workflow."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_transport"
REPORT_DIR = ROOT / "reports" / "testnet_mock_transport"

def main() -> int:
    unlock_mod = importlib.import_module("src.runtime_integrations.testnet_mock_transport.unlock_request_dry_run")

    # Create unlock requests for all gate types
    results = []
    for gate in ("submit", "cancel", "reconciliation"):
        req = unlock_mod.create_unlock_request(gate)
        unlock_mod.write_request(req, OUT_DIR / f"unlock_request_{gate}.json")
        results.append(req.to_dict())
        print(f"  {gate} gate: decision={req.decision}, approved={req.approved}, blockers={len(req.blockers)}")

    import json
    (OUT_DIR / "unlock_requests_all.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    report = unlock_mod.render_report()
    (REPORT_DIR / "unlock_request_dry_run.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "unlock_request_dry_run.md").write_text(report, encoding="utf-8")

    print(f"unlock_request_dry_run: {len(results)} requests, all DENY")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
