"""Runner: request signing fixture validation."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_transport"
REPORT_DIR = ROOT / "reports" / "testnet_mock_transport"

def main() -> int:
    signing_mod = importlib.import_module("src.runtime_integrations.testnet_mock_transport.request_signing_fixture")

    envelope = signing_mod.build_fixture_envelope("POST", "/api/v3/order", '{"symbol":"BTCUSDT"}')
    signing_mod.write_envelope(envelope, OUT_DIR / "request_signing_fixture.json")

    valid = signing_mod.validate_envelope(envelope.to_dict())
    report = signing_mod.render_report()
    (REPORT_DIR / "request_signing_fixture.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "request_signing_fixture.md").write_text(report, encoding="utf-8")

    print(f"request_signing_fixture: envelope_id={envelope.envelope_id}, valid={valid}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
