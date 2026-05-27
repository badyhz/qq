"""T1521 - Frozen Backlog Inventory."""
from __future__ import annotations

from dataclasses import dataclass

from core.frozen_backlog_inventory_record import FrozenBacklogInventoryRecord


@dataclass(frozen=True)
class FrozenBacklogInventory:
    """Immutable inventory of all frozen backlog files.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    inventory_id: str
    records: tuple[FrozenBacklogInventoryRecord, ...]
    total_count: int
    high_risk_count: int
    medium_risk_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "inventory_id": self.inventory_id,
            "records": [r.to_dict() for r in self.records],
            "total_count": self.total_count,
            "high_risk_count": self.high_risk_count,
            "medium_risk_count": self.medium_risk_count,
        }


# --- Hardcoded inventory of 22 frozen backlog files ---

_HIGH_RECORDS: tuple[FrozenBacklogInventoryRecord, ...] = (
    FrozenBacklogInventoryRecord(
        file_path="core/live_runner.py",
        risk_class="HIGH",
        category="LIVE_RUNNER",
        allowed_actions=("review", "read", "lint", "typecheck"),
        forbidden_actions=("execute", "import_runtime", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review", "human_approval"),
        promotion_readiness_default=0.0,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/live_playbook.py",
        risk_class="HIGH",
        category="LIVE_PLAYBOOK",
        allowed_actions=("review", "read", "lint", "typecheck"),
        forbidden_actions=("execute", "import_runtime", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review", "human_approval"),
        promotion_readiness_default=0.0,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/submit_approved_candidates.py",
        risk_class="HIGH",
        category="SUBMIT",
        allowed_actions=("review", "read", "lint", "typecheck"),
        forbidden_actions=("execute", "import_runtime", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review", "human_approval"),
        promotion_readiness_default=0.0,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/run_testnet_order_smoke.py",
        risk_class="HIGH",
        category="TESTNET_SMOKE",
        allowed_actions=("review", "read", "lint", "typecheck"),
        forbidden_actions=("execute", "import_runtime", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review", "human_approval"),
        promotion_readiness_default=0.0,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/run_signal_testnet_trial.py",
        risk_class="HIGH",
        category="TESTNET_SMOKE",
        allowed_actions=("review", "read", "lint", "typecheck"),
        forbidden_actions=("execute", "import_runtime", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review", "human_approval"),
        promotion_readiness_default=0.0,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/run_spot_testnet_acceptance.py",
        risk_class="HIGH",
        category="TESTNET_SMOKE",
        allowed_actions=("review", "read", "lint", "typecheck"),
        forbidden_actions=("execute", "import_runtime", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review", "human_approval"),
        promotion_readiness_default=0.0,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/safe_flatten_testnet_symbol.py",
        risk_class="HIGH",
        category="FLATTEN",
        allowed_actions=("review", "read", "lint", "typecheck"),
        forbidden_actions=("execute", "import_runtime", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review", "human_approval"),
        promotion_readiness_default=0.0,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/replay_shadow_order_plans_as_testnet_dry.py",
        risk_class="HIGH",
        category="REPLAY_SUBMIT",
        allowed_actions=("review", "read", "lint", "typecheck"),
        forbidden_actions=("execute", "import_runtime", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review", "human_approval"),
        promotion_readiness_default=0.0,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/submit_replayed_testnet_payload.py",
        risk_class="HIGH",
        category="SUBMIT",
        allowed_actions=("review", "read", "lint", "typecheck"),
        forbidden_actions=("execute", "import_runtime", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review", "human_approval"),
        promotion_readiness_default=0.0,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
)

_MEDIUM_RECORDS: tuple[FrozenBacklogInventoryRecord, ...] = (
    FrozenBacklogInventoryRecord(
        file_path="scripts/run_controlled_testnet_shift.py",
        risk_class="MEDIUM",
        category="OPERATIONAL_SHADOW",
        allowed_actions=("review", "read", "lint", "typecheck", "dry_run"),
        forbidden_actions=("execute", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review"),
        promotion_readiness_default=0.2,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/run_daily_shadow_scan_pipeline.py",
        risk_class="MEDIUM",
        category="OPERATIONAL_SHADOW",
        allowed_actions=("review", "read", "lint", "typecheck", "dry_run"),
        forbidden_actions=("execute", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review"),
        promotion_readiness_default=0.2,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/run_next_shadow_experiment_plan.py",
        risk_class="MEDIUM",
        category="OPERATIONAL_SHADOW",
        allowed_actions=("review", "read", "lint", "typecheck", "dry_run"),
        forbidden_actions=("execute", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review"),
        promotion_readiness_default=0.2,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/run_observation_shift_runtime.py",
        risk_class="MEDIUM",
        category="OPERATIONAL_SHADOW",
        allowed_actions=("review", "read", "lint", "typecheck", "dry_run"),
        forbidden_actions=("execute", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review"),
        promotion_readiness_default=0.2,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/run_remediation_shadow_only_loop.py",
        risk_class="MEDIUM",
        category="OPERATIONAL_SHADOW",
        allowed_actions=("review", "read", "lint", "typecheck", "dry_run"),
        forbidden_actions=("execute", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review"),
        promotion_readiness_default=0.2,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/run_replay_submit_batch.py",
        risk_class="MEDIUM",
        category="OPERATIONAL_SHADOW",
        allowed_actions=("review", "read", "lint", "typecheck", "dry_run"),
        forbidden_actions=("execute", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review"),
        promotion_readiness_default=0.2,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/run_right_breakout_param_observation.py",
        risk_class="MEDIUM",
        category="OPERATIONAL_SHADOW",
        allowed_actions=("review", "read", "lint", "typecheck", "dry_run"),
        forbidden_actions=("execute", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review"),
        promotion_readiness_default=0.2,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/run_right_breakout_scan_dry.py",
        risk_class="MEDIUM",
        category="OPERATIONAL_SHADOW",
        allowed_actions=("review", "read", "lint", "typecheck", "dry_run"),
        forbidden_actions=("execute", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review"),
        promotion_readiness_default=0.2,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/run_shadow_observation_experiments.py",
        risk_class="MEDIUM",
        category="OPERATIONAL_SHADOW",
        allowed_actions=("review", "read", "lint", "typecheck", "dry_run"),
        forbidden_actions=("execute", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review"),
        promotion_readiness_default=0.2,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/run_shadow_sample_collection_pipeline.py",
        risk_class="MEDIUM",
        category="OPERATIONAL_SHADOW",
        allowed_actions=("review", "read", "lint", "typecheck", "dry_run"),
        forbidden_actions=("execute", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review"),
        promotion_readiness_default=0.2,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/run_shadow_universe_collector.py",
        risk_class="MEDIUM",
        category="OPERATIONAL_SHADOW",
        allowed_actions=("review", "read", "lint", "typecheck", "dry_run"),
        forbidden_actions=("execute", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review"),
        promotion_readiness_default=0.2,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/verify_risk_release_flow.py",
        risk_class="MEDIUM",
        category="VERIFICATION",
        allowed_actions=("review", "read", "lint", "typecheck", "dry_run"),
        forbidden_actions=("execute", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review"),
        promotion_readiness_default=0.3,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
    FrozenBacklogInventoryRecord(
        file_path="scripts/verify_testnet_repair_scenarios.py",
        risk_class="MEDIUM",
        category="VERIFICATION",
        allowed_actions=("review", "read", "lint", "typecheck", "dry_run"),
        forbidden_actions=("execute", "submit", "modify"),
        required_evidence=("dry_run_log", "risk_review"),
        promotion_readiness_default=0.3,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    ),
)

_ALL_RECORDS: tuple[FrozenBacklogInventoryRecord, ...] = _HIGH_RECORDS + _MEDIUM_RECORDS

FROZEN_BACKLOG_INVENTORY: FrozenBacklogInventory = FrozenBacklogInventory(
    inventory_id="frozen-backlog-batch1",
    records=_ALL_RECORDS,
    total_count=len(_ALL_RECORDS),
    high_risk_count=len(_HIGH_RECORDS),
    medium_risk_count=len(_MEDIUM_RECORDS),
)
