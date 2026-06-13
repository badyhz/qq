"""Tests for T21001 — Phase 5: Testnet Dry-Run Orchestrator + Operator Console + Final Handoff.

Covers:
- Testnet dry-run: no real submit, simulated fills
- Operator console: correct status, forbidden modes
- Final handoff: all modules listed, conclusions correct
- All safety boundaries enforced
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.testnet_dry_run_orchestrator import (
    FORBIDDEN_REAL_ACTIONS,
    OrderIntent,
    OrderLifecycleEvent,
    StabilityScore,
    build_order_intent,
    compute_lifecycle_hash,
    run_orchestrator,
    simulate_order_submit,
    simulate_risk_precheck,
)
from core.operator_console import (
    FORBIDDEN_MODES,
    OperatorConsoleStatus,
    build_operator_console,
    compute_console_hash,
)
from core.final_handoff_pack import (
    FinalHandoffPack,
    build_final_handoff_pack,
    compute_handoff_hash,
)


# --- Testnet Dry-Run Orchestrator Tests ---

class TestDryRunOrchestrator:
    def test_build_intent(self):
        intent = build_order_intent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "test_v1")
        assert intent.symbol == "BTCUSDT"
        assert intent.side == "BUY"
        assert intent.dry_run is True

    def test_risk_precheck_passes(self):
        intent = build_order_intent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "test_v1")
        passed, reason = simulate_risk_precheck(intent)
        assert passed is True

    def test_simulate_fill(self):
        intent = build_order_intent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "test_v1")
        event = simulate_order_submit(intent, True)
        assert event.stage == "SIMULATED_FILL"
        assert event.dry_run is True
        assert event.no_real_action is True
        assert event.simulated_fill_price > 0

    def test_simulate_reject_on_risk(self):
        intent = build_order_intent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "test_v1")
        event = simulate_order_submit(intent, False)
        assert event.stage == "SIMULATED_REJECT"
        assert event.dry_run is True

    def test_run_orchestrator(self):
        intents = [
            build_order_intent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "test_v1"),
            build_order_intent("ETHUSDT", "SELL", "MARKET", 0.01, 3000.0, "test_v1"),
        ]
        events, score = run_orchestrator(intents, release_hold="HOLD")
        assert len(events) == 2
        assert score.total_intents == 2
        assert score.successful_simulations == 2
        assert score.dry_run is True

    def test_release_hold_mismatch(self):
        intents = [build_order_intent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "test_v1")]
        with pytest.raises(ValueError, match="release_hold"):
            run_orchestrator(intents, release_hold="WRONG")

    def test_no_forbidden_real_actions(self):
        intents = [build_order_intent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "test_v1")]
        events, _ = run_orchestrator(intents)
        for event in events:
            event_str = str(event.to_dict())
            for action in FORBIDDEN_REAL_ACTIONS:
                assert action not in event_str

    def test_slippage_simulated(self):
        intent = build_order_intent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "test_v1")
        event = simulate_order_submit(intent, True)
        assert event.simulated_slippage_bps > 0

    def test_latency_simulated(self):
        intent = build_order_intent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "test_v1")
        event = simulate_order_submit(intent, True)
        assert event.simulated_latency_ms > 0


class TestDryRunDeterministic:
    def test_hash_stable(self):
        intents = [build_order_intent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "test_v1")]
        events, _ = run_orchestrator(intents)
        h1 = compute_lifecycle_hash(events)
        h2 = compute_lifecycle_hash(events)
        assert h1 == h2


# --- Operator Console Tests ---

class TestOperatorConsole:
    def test_build_console(self):
        console = build_operator_console()
        assert console.current_mode in ("SHADOW_ONLY", "TESTNET_DRY_RUN_PREP")
        assert console.real_submit_allowed is False
        assert console.testnet_submit_allowed is False
        assert console.dry_run_allowed is True
        assert console.dry_run is True

    def test_console_with_blockers(self):
        console = build_operator_console(blockers=["test_blocker"])
        assert console.system_healthy is False
        assert "test_blocker" in console.critical_blockers

    def test_console_healthy(self):
        console = build_operator_console(blockers=[])
        assert console.system_healthy is True

    def test_no_forbidden_modes(self):
        console = build_operator_console()
        assert console.current_mode not in FORBIDDEN_MODES

    def test_submit_permission_no_submit(self):
        console = build_operator_console()
        assert console.submit_permission == "NO_SUBMIT"

    def test_console_hash_stable(self):
        console = build_operator_console()
        h1 = compute_console_hash(console)
        h2 = compute_console_hash(console)
        assert h1 == h2


# --- Final Handoff Pack Tests ---

class TestFinalHandoffPack:
    def test_build_pack(self):
        pack = build_final_handoff_pack(release_hold="HOLD")
        assert pack.total_modules == 10
        assert pack.completed_modules == 7
        assert pack.dry_run is True

    def test_conclusions_present(self):
        pack = build_final_handoff_pack()
        assert "OFFLINE_GOVERNANCE_COMPLETE" in pack.final_conclusions
        assert "SHADOW_TO_TESTNET_PREPARED" in pack.final_conclusions
        assert "TESTNET_DRY_RUN_SIMULATION_READY" in pack.final_conclusions
        assert "REAL_TRADING_NOT_ALLOWED" in pack.final_conclusions

    def test_no_real_trading_conclusion(self):
        pack = build_final_handoff_pack()
        assert "REAL_TRADING_NOT_ALLOWED" in pack.final_conclusions

    def test_placeholders_present(self):
        pack = build_final_handoff_pack()
        placeholders = [m for m in pack.modules if m.status == "PLACEHOLDER"]
        assert len(placeholders) == 3

    def test_completed_modules_correct(self):
        pack = build_final_handoff_pack()
        completed = [m for m in pack.modules if m.status == "COMPLETE"]
        assert len(completed) == 7
        for m in completed:
            assert m.tests_passed is True
            assert m.reports_generated is True
            assert m.evidence_recorded is True

    def test_remaining_risks(self):
        pack = build_final_handoff_pack()
        assert len(pack.remaining_risks) > 0

    def test_next_prd_recommendations(self):
        pack = build_final_handoff_pack()
        assert len(pack.next_prd_recommendations) > 0

    def test_handoff_hash_stable(self):
        pack = build_final_handoff_pack()
        h1 = compute_handoff_hash(pack)
        h2 = compute_handoff_hash(pack)
        assert h1 == h2

    def test_release_hold_mismatch(self):
        with pytest.raises(ValueError, match="release_hold"):
            build_final_handoff_pack(release_hold="WRONG")


# --- Integration Safety Tests ---

class TestGlobalSafety:
    def test_orchestrator_no_real_submit(self):
        intents = [build_order_intent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "test")]
        events, score = run_orchestrator(intents)
        for event in events:
            assert event.dry_run is True
            assert event.no_real_action is True

    def test_console_no_real_submit(self):
        console = build_operator_console()
        assert console.real_submit_allowed is False
        assert console.testnet_submit_allowed is False

    def test_handoff_real_trading_not_allowed(self):
        pack = build_final_handoff_pack()
        assert "REAL_TRADING_NOT_ALLOWED" in pack.final_conclusions
