#!/usr/bin/env python3
"""Wave 1: Sandbox adapter contract check."""
import json, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    from src.runtime_integrations.testnet_sandbox.adapter_contract import validate_contract_implementation, write_contract_validation
    from src.runtime_integrations.testnet_sandbox.simulated_exchange_adapter import SimulatedExchangeAdapter
    from src.runtime_integrations.testnet_sandbox.sandbox_types import ConnectionConfig

    # Validate contract
    result = validate_contract_implementation(SimulatedExchangeAdapter)
    write_contract_validation(result, "SimulatedExchangeAdapter", ROOT / "data" / "runtime" / "testnet_sandbox" / "adapter_contract_check.json")

    # Smoke test adapter
    adapter = SimulatedExchangeAdapter()
    config = ConnectionConfig("PLACEHOLDER_KEY", "PLACEHOLDER_SECRET", "https://testnet.binance.vision", True)
    config_val = adapter.validate_connection_config(config)
    intent = adapter.build_order_intent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "SIG_001")
    intent_val = adapter.validate_order_intent(intent)
    submit = adapter.simulate_submit(intent)
    cancel = adapter.simulate_cancel(submit.order_id, "BTCUSDT")
    balance = adapter.get_simulated_balance("USDT")
    positions = adapter.get_simulated_positions()

    # Validate results
    checks = {
        "contract_valid": result[0],
        "missing_methods": list(result[1]),
        "config_valid": config_val.valid,
        "intent_valid": intent_val.valid,
        "submit_simulated": submit.simulated,
        "submit_real_submit_false": not submit.real_submit,
        "submit_testnet_submit_false": not submit.testnet_submit,
        "submit_no_submit_enforced": submit.no_submit_enforced,
        "cancel_simulated": cancel.simulated,
        "balance_simulated": balance.simulated,
        "positions_count": len(positions),
    }
    (ROOT / "data" / "runtime" / "testnet_sandbox" / "adapter_smoke_test.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")

    # Report
    lines = ["# Sandbox Adapter Contract Check", "", f"Contract valid: {result[0]}", f"Missing methods: {result[1]}", "", "## Smoke Test", ""]
    for k, v in checks.items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Conclusion", "", "SANDBOX_ADAPTER_INTERFACE_VALID", ""])
    (ROOT / "reports" / "sandbox_adapter_contract_report.md").write_text("\n".join(lines), encoding="utf-8")

    ok = result[0] and config_val.valid and intent_val.valid and submit.simulated and not submit.real_submit
    print(f"Adapter contract: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
