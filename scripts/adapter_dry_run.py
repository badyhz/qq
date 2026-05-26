"""T759 — Single-Call Dry-Run Harness.

Simulates ONE future adapter call through the full safety stack.
NO network. NO secrets. NO API requests.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.credential_manager import CredentialManager
from core.network_sandbox import NetworkSandbox
from core.real_adapter_policy import RealAdapterPolicy
from core.manual_approval_gate import ManualApprovalGate
from core.live_capability_registry import LiveCapabilityRegistry, LiveCapability
from core.adapter_preflight import AdapterPreflightValidator
from core.workflow_observability import WorkflowObservability, EventType
from adapters.claude_api_adapter import ClaudeAPIAdapter


ADAPTER_ID = "claude_api"
ACTION = "single_test_call"


async def main():
    # ── 1. Set up all safety components ──────────────────────────────

    cred_manager = CredentialManager()
    # Register adapter but do NOT set env var — simulates no real credentials
    cred_manager.register_adapter(ADAPTER_ID, env_var="DRY_RUN_NO_KEY", required=False)

    network_sandbox = NetworkSandbox(mode="simulation")

    real_adapter_policy = RealAdapterPolicy()
    real_adapter_policy.register(
        ADAPTER_ID,
        {"endpoint": "https://api.anthropic.com", "cross_adapter_refs": {}},
    )
    real_adapter_policy.add_to_allowlist(ADAPTER_ID)

    approval_gate = ManualApprovalGate(default_ttl_seconds=3600)

    capability_registry = LiveCapabilityRegistry()
    capability_registry.register_capability(LiveCapability.LIVE_EXECUTION, ADAPTER_ID, requires_approval=False)

    preflight = AdapterPreflightValidator(
        credential_manager=cred_manager,
        network_sandbox=network_sandbox,
        real_adapter_policy=real_adapter_policy,
        approval_gate=approval_gate,
        capability_registry=capability_registry,
    )

    # ── 2. Run preflight check ───────────────────────────────────────

    print("=== PREFLIGHT ===")
    result = preflight.validate(ADAPTER_ID, ACTION)
    print(f"  Status: {result.status.value}")
    for c in result.checks:
        marker = "PASS" if c.passed else "FAIL"
        print(f"  [{marker}] {c.name}: {c.detail}")

    # ── 3. Request and approve ───────────────────────────────────────

    print("\n=== APPROVAL ===")
    token = approval_gate.request_approval(ACTION, ADAPTER_ID)
    print(f"  Token: {token[:8]}...")
    print(f"  Approved: {approval_gate.is_approved(ACTION, ADAPTER_ID)}")

    approval_gate.approve(token)
    print(f"  After approve: {approval_gate.is_approved(ACTION, ADAPTER_ID)}")

    # ── 4. Execute dry-run ───────────────────────────────────────────

    print("\n=== DRY RUN ===")
    adapter = ClaudeAPIAdapter()

    task_id = "dry_run_task_001"
    prompt = "Hello, this is a dry run test."

    request_id = await adapter.submit_task(task_id, prompt)
    print(f"  Request ID: {request_id[:8]}...")

    result = await adapter.poll(request_id)
    print(f"  Status: {result.status.value}")
    print(f"  Duration: {result.duration_ms:.1f}ms")
    print(f"  Output: {result.output[:80]}...")

    # ── 5. Record budget ─────────────────────────────────────────────

    print("\n=== BUDGET ===")
    sim_input = 10
    sim_output = 50
    sim_cost = 0.001
    adapter._total_input_tokens += sim_input
    adapter._total_output_tokens += sim_output
    adapter._total_cost_usd += sim_cost

    status = await adapter.status()
    print(f"  Total input tokens: {status['total_input_tokens']}")
    print(f"  Total output tokens: {status['total_output_tokens']}")
    print(f"  Total cost (USD): {status['total_cost_usd']:.4f}")
    print(f"  Budget ceiling: {status['budget_ceiling_usd']:.2f}")

    # ── 6. Emit observability ────────────────────────────────────────

    print("\n=== OBSERVABILITY ===")
    obs = WorkflowObservability()
    obs.emit(EventType.TASK_STARTED, task_id=task_id, adapter_id=ADAPTER_ID)
    obs.emit(EventType.TASK_COMPLETED, task_id=task_id, adapter_id=ADAPTER_ID)

    summary = obs.summary()
    print(f"  Total events: {summary['total']}")
    print(f"  Counts: {summary['counts']}")

    timeline = obs.timeline(task_id)
    for evt in timeline:
        print(f"  - {evt['event']}: {evt['task_id']}")


if __name__ == "__main__":
    asyncio.run(main())
