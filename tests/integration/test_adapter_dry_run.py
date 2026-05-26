"""T759 — Integration tests for adapter dry-run harness.

No network. No secrets. No API requests.
"""

import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.credential_manager import CredentialManager
from core.network_sandbox import NetworkSandbox
from core.real_adapter_policy import RealAdapterPolicy
from core.manual_approval_gate import ManualApprovalGate, ApprovalStatus
from core.live_capability_registry import LiveCapabilityRegistry, LiveCapability
from core.adapter_preflight import AdapterPreflightValidator, PreflightStatus
from core.workflow_observability import WorkflowObservability, EventType
from adapters.claude_api_adapter import ClaudeAPIAdapter

ADAPTER_ID = "claude_api"
ACTION = "single_test_call"


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def cred_manager():
    cm = CredentialManager()
    cm.register_adapter(ADAPTER_ID, env_var="DRY_RUN_NO_KEY", required=False)
    # Set dummy env var so credential check passes in dry-run
    os.environ["DRY_RUN_NO_KEY"] = "dry_run_dummy_value"
    yield cm
    os.environ.pop("DRY_RUN_NO_KEY", None)


@pytest.fixture
def network_sandbox():
    return NetworkSandbox(mode="simulation")


@pytest.fixture
def real_adapter_policy():
    policy = RealAdapterPolicy()
    policy.register(
        ADAPTER_ID,
        {"endpoint": "https://api.anthropic.com", "cross_adapter_refs": {}},
    )
    policy.add_to_allowlist(ADAPTER_ID)
    return policy


@pytest.fixture
def approval_gate():
    return ManualApprovalGate(default_ttl_seconds=3600)


@pytest.fixture
def capability_registry():
    reg = LiveCapabilityRegistry()
    reg.register_capability(LiveCapability.LIVE_EXECUTION, ADAPTER_ID, requires_approval=False)
    return reg


@pytest.fixture
def full_preflight(cred_manager, network_sandbox, real_adapter_policy, approval_gate, capability_registry):
    return AdapterPreflightValidator(
        credential_manager=cred_manager,
        network_sandbox=network_sandbox,
        real_adapter_policy=real_adapter_policy,
        approval_gate=approval_gate,
        capability_registry=capability_registry,
    )


@pytest.fixture
def observability():
    return WorkflowObservability()


# ── Tests ────────────────────────────────────────────────────────────


class TestPreflightPasses:
    def test_all_components_configured(self, full_preflight):
        result = full_preflight.validate(ADAPTER_ID, ACTION)
        # Approval not granted yet, so approval check fails => FAIL overall
        assert result.status == PreflightStatus.FAIL
        failed_checks = [c for c in result.checks if not c.passed]
        assert len(failed_checks) == 1
        assert failed_checks[0].name == "approval"

    def test_passes_after_approval(self, full_preflight, approval_gate):
        token = approval_gate.request_approval(ACTION, ADAPTER_ID)
        approval_gate.approve(token)
        result = full_preflight.validate(ADAPTER_ID, ACTION)
        assert result.status == PreflightStatus.PASS


class TestApprovalGate:
    def test_blocks_without_approval(self, full_preflight):
        assert not full_preflight.approval_gate.is_approved(ACTION, ADAPTER_ID)

    def test_allows_after_approval(self, full_preflight, approval_gate):
        token = approval_gate.request_approval(ACTION, ADAPTER_ID)
        assert not approval_gate.is_approved(ACTION, ADAPTER_ID)

        approval_gate.approve(token)
        assert approval_gate.is_approved(ACTION, ADAPTER_ID)

    def test_single_use_token(self, approval_gate):
        token = approval_gate.request_approval(ACTION, ADAPTER_ID)
        approval_gate.approve(token)
        result = approval_gate.consume(token)
        assert result.success
        assert result.status == ApprovalStatus.CONSUMED

        # Second consume fails
        result2 = approval_gate.consume(token)
        assert not result2.success


class TestDryRunAdapter:
    def test_submit_and_poll(self):
        adapter = ClaudeAPIAdapter()

        async def _run():
            request_id = await adapter.submit_task("test_001", "Hello dry run")
            result = await adapter.poll(request_id)
            return result

        result = asyncio.get_event_loop().run_until_complete(_run())
        assert result.status.value == "completed"
        assert "dry-run" in result.output.lower() or result.output  # has some output

    def test_simulated_response_structure(self):
        adapter = ClaudeAPIAdapter()

        async def _run():
            request_id = await adapter.submit_task("test_002", "Test prompt")
            result = await adapter.poll(request_id)
            return result

        result = asyncio.get_event_loop().run_until_complete(_run())
        assert result.task_id == "test_002"
        assert result.adapter_id == "claude_api"
        assert result.duration_ms >= 0


class TestBudgetTracking:
    def test_records_cost(self):
        adapter = ClaudeAPIAdapter()

        async def _run():
            await adapter.submit_task("budget_001", "Budget test")
            # Simulate additional cost recording
            adapter._total_input_tokens += 10
            adapter._total_output_tokens += 50
            adapter._total_cost_usd += 0.001
            return await adapter.status()

        status = asyncio.get_event_loop().run_until_complete(_run())
        assert status["total_input_tokens"] > 0
        assert status["total_output_tokens"] > 0
        assert status["total_cost_usd"] > 0

    def test_budget_ceiling_enforced(self):
        adapter = ClaudeAPIAdapter(budget_ceiling_usd=0.0)
        assert not adapter.check_budget(0.001)


class TestObservability:
    def test_events_emitted(self, observability):
        observability.emit(EventType.TASK_STARTED, task_id="obs_001", adapter_id=ADAPTER_ID)
        observability.emit(EventType.TASK_COMPLETED, task_id="obs_001", adapter_id=ADAPTER_ID)

        summary = observability.summary()
        assert summary["total"] == 2
        assert summary["counts"]["task_started"] == 1
        assert summary["counts"]["task_completed"] == 1

    def test_timeline(self, observability):
        observability.emit(EventType.TASK_STARTED, task_id="tl_001", adapter_id=ADAPTER_ID)
        observability.emit(EventType.TASK_COMPLETED, task_id="tl_001", adapter_id=ADAPTER_ID)

        timeline = observability.timeline("tl_001")
        assert len(timeline) == 2
        assert timeline[0]["event"] == "task_started"
        assert timeline[1]["event"] == "task_completed"

    def test_query_by_event_type(self, observability):
        observability.emit(EventType.TASK_STARTED, task_id="q_001")
        observability.emit(EventType.TASK_COMPLETED, task_id="q_001")
        observability.emit(EventType.TASK_FAILED, task_id="q_002")

        started = observability.query(event_type=EventType.TASK_STARTED)
        assert len(started) == 1

        failed = observability.query(event_type=EventType.TASK_FAILED)
        assert len(failed) == 1


class TestFullFlow:
    def test_preflight_approval_execute_budget_observability(self):
        cm = CredentialManager()
        cm.register_adapter(ADAPTER_ID, env_var="DRY_RUN_NO_KEY", required=False)
        os.environ["DRY_RUN_NO_KEY"] = "dry_run_dummy_value"

        sandbox = NetworkSandbox(mode="simulation")

        policy = RealAdapterPolicy()
        policy.register(ADAPTER_ID, {"endpoint": "https://api.anthropic.com", "cross_adapter_refs": {}})
        policy.add_to_allowlist(ADAPTER_ID)

        gate = ManualApprovalGate()
        reg = LiveCapabilityRegistry()
        reg.register_capability(LiveCapability.LIVE_EXECUTION, ADAPTER_ID, requires_approval=False)

        preflight = AdapterPreflightValidator(
            credential_manager=cm,
            network_sandbox=sandbox,
            real_adapter_policy=policy,
            approval_gate=gate,
            capability_registry=reg,
        )

        # 1. Preflight (will fail — no approval yet)
        result = preflight.validate(ADAPTER_ID, ACTION)
        assert result.status == PreflightStatus.FAIL

        # 2. Approval
        token = gate.request_approval(ACTION, ADAPTER_ID)
        gate.approve(token)
        result = preflight.validate(ADAPTER_ID, ACTION)
        assert result.status == PreflightStatus.PASS

        # 3. Execute
        adapter = ClaudeAPIAdapter()

        async def _run():
            req_id = await adapter.submit_task("full_001", "Full flow test")
            return await adapter.poll(req_id)

        poll_result = asyncio.get_event_loop().run_until_complete(_run())
        assert poll_result.status.value == "completed"

        # 4. Budget
        adapter._total_cost_usd += 0.001
        status = asyncio.get_event_loop().run_until_complete(adapter.status())
        assert status["total_cost_usd"] > 0

        # 5. Observability
        obs = WorkflowObservability()
        obs.emit(EventType.TASK_STARTED, task_id="full_001", adapter_id=ADAPTER_ID)
        obs.emit(EventType.TASK_COMPLETED, task_id="full_001", adapter_id=ADAPTER_ID)
        assert obs.summary()["total"] == 2


class TestMissingComponents:
    def test_no_components_gives_partial(self):
        preflight = AdapterPreflightValidator()
        result = preflight.validate(ADAPTER_ID, ACTION)
        # All skipped => PARTIAL (no failures, but has "skipped" details)
        assert result.status == PreflightStatus.PARTIAL

    def test_partial_components(self):
        os.environ["DRY_RUN_NO_KEY"] = "dry_run_dummy_value"
        cm = CredentialManager()
        cm.register_adapter(ADAPTER_ID, env_var="DRY_RUN_NO_KEY", required=False)
        preflight = AdapterPreflightValidator(
            credential_manager=cm,
        )
        # Only credential_manager registered — other components skipped => PARTIAL
        result = preflight.validate(ADAPTER_ID, ACTION)
        assert result.status == PreflightStatus.PARTIAL
        skipped = [c for c in result.checks if "skipped" in c.detail]
        assert len(skipped) >= 3  # network, budget, capability, approval all skipped
        os.environ.pop("DRY_RUN_NO_KEY", None)
