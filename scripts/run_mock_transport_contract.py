"""Runner: mock transport contract."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_transport"
REPORT_DIR = ROOT / "reports" / "testnet_mock_transport"

def main() -> int:
    contract_mod = importlib.import_module("src.runtime_integrations.testnet_mock_transport.mock_transport_contract")
    validator_mod = importlib.import_module("src.runtime_integrations.testnet_mock_transport.mock_transport_validator")

    report = contract_mod.render_report()
    (REPORT_DIR / "mock_transport_contract.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "mock_transport_contract.md").write_text(report, encoding="utf-8")

    # Test dispatch
    fixtures = contract_mod.get_available_fixtures()
    dispatch_results = []
    for fixture in fixtures:
        env = contract_mod.create_request_envelope("GET", f"/api/v3/{fixture}")
        resp = contract_mod.dispatch_mock(fixture, env.request_id)
        dispatch_results.append({"fixture": fixture, "status": resp.status_code, "request_id": env.request_id})
    contract_mod.write_contract({"fixtures": list(fixtures), "dispatch_results": dispatch_results}, OUT_DIR / "mock_transport_contract.json")

    checks = validator_mod.validate_contract(report)
    validator_mod.write_checks(checks, OUT_DIR / "mock_transport_contract_checks.json")

    passed = sum(1 for c in checks if c.passed)
    print(f"mock_transport_contract: {len(fixtures)} fixtures, {passed}/{len(checks)} checks passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
