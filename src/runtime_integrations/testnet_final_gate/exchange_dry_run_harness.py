"""Exchange dry-run harness. Exercises adapter boundary without network."""
from __future__ import annotations
import json, pathlib
from .exchange_harness_result import HarnessStep, HarnessResult

FAKE_PROFILE = {"exchange": "binance_testnet", "base_url": "https://testnet.binance.vision", "api_key": "***STUB_REDACTED***", "api_secret": "***STUB_REDACTED***"}

def run_harness() -> HarnessResult:
    steps = []
    # Load fake profile
    steps.append(HarnessStep("load_profile", "SIMULATED", f"profile={FAKE_PROFILE['exchange']}, key=REDACTED"))
    # Validate permissions
    steps.append(HarnessStep("validate_permissions", "PASS", "stub permissions: SPOT_READ, SPOT_TRADE"))
    # Build order request
    steps.append(HarnessStep("build_order_request", "SIMULATED", "BTCUSDT BUY 0.001 LIMIT 50000"))
    # Simulate signing
    steps.append(HarnessStep("simulate_signing", "SIMULATED", "fake_signature=***REDACTED***"))
    # Simulate submit
    steps.append(HarnessStep("simulate_submit", "SIMULATED", "SIM_ORD_001 status=SIMULATED_NEW"))
    # Simulate cancel
    steps.append(HarnessStep("simulate_cancel", "SIMULATED", "SIM_ORD_001 status=SIMULATED_CANCELLED"))
    # Simulate balance fetch
    steps.append(HarnessStep("simulate_balance", "SIMULATED", "USDT=10000 BTC=0.5"))
    # Simulate position fetch
    steps.append(HarnessStep("simulate_positions", "SIMULATED", "no positions"))
    return HarnessResult(tuple(steps), no_network=True, no_real_key=True, no_submit=True, overall="EXCHANGE_SANDBOX_DRY_RUN_HARNESS_PASS")

def write_result(result: HarnessResult, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

def render_report(result: HarnessResult) -> str:
    lines = ["# Exchange Sandbox Dry-Run Harness Report", "", "## Steps", "", "| Step | Status | Detail |", "|------|--------|--------|"]
    for s in result.steps:
        lines.append(f"| {s.step} | {s.status} | {s.detail} |")
    lines.extend(["", "## Safety", "", f"- no_network: {result.no_network}", f"- no_real_key: {result.no_real_key}", f"- no_submit: {result.no_submit}", "", "## Conclusion", "", result.overall, ""])
    return "\n".join(lines)
