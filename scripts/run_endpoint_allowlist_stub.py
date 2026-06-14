"""Runner: endpoint_allowlist_stub."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_dry_execution_rehearsal"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_dry_execution_rehearsal"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_dry_execution_rehearsal.endpoint_allowlist_stub")
    obj = mod.create_stub()
    mod.write_stub(obj, OUT_DIR / "endpoint_allowlist_stub.json")
    report = mod.render_report(obj)
    (REPORT_DIR / "endpoint_allowlist_stub_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "endpoint_allowlist_stub_report.md").write_text(report, encoding="utf-8")
    print(f"endpoint_allowlist_stub: created")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
