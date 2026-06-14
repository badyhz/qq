"""Runner: adapter skeleton dry-run."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_transport"
REPORT_DIR = ROOT / "reports" / "testnet_mock_transport"

def main() -> int:
    skeleton_mod = importlib.import_module("src.runtime_integrations.testnet_mock_transport.adapter_skeleton")

    # Build and validate order request
    req = skeleton_mod.build_order_request("BTCUSDT", "BUY", "LIMIT", "0.001", "50000.00")
    validation = skeleton_mod.validate_order_request(req)

    # Dry-run operations
    submit_result = skeleton_mod.submit_order_dry_run(req)
    cancel_result = skeleton_mod.cancel_order_dry_run("MOCK_001")
    balance_result = skeleton_mod.reconcile_balance_dry_run()
    position_result = skeleton_mod.reconcile_position_dry_run()

    data = {
        "order_request": req.to_dict(),
        "validation": validation,
        "submit_dry_run": submit_result.to_dict(),
        "cancel_dry_run": cancel_result.to_dict(),
        "balance_dry_run": balance_result.to_dict(),
        "position_dry_run": position_result.to_dict(),
    }
    skeleton_mod.write_skeleton(data, OUT_DIR / "adapter_skeleton.json")

    report = skeleton_mod.render_report()
    (REPORT_DIR / "adapter_skeleton.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "adapter_skeleton.md").write_text(report, encoding="utf-8")

    print(f"adapter_skeleton: order_valid={validation['valid']}, submit_simulated={submit_result.simulated}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
