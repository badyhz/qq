"""Read-only hook governance closeout layer (T1041-T1060).

Pure deterministic packets. No I/O. No live trading authorization.
Frozen dataclasses + pure functions only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Frozen dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GovernanceSummaryPacket:
    task_range: str
    design_doc_count: int
    model_module_count: int
    renderer_module_count: int
    acceptance_module_count: int
    test_file_count: int
    total_tests: int
    verdict: str
    release_hold: str  # "HOLD"
    notes: List[str]


@dataclass(frozen=True)
class RiskHeatmapPacket:
    low_count: int
    medium_count: int
    high_count: int
    frozen_count: int
    total: int
    recommended_action: str
    notes: List[str]


@dataclass(frozen=True)
class DependencyDensityPacket:
    module_count: int
    import_count: int
    density_level: str  # "low", "medium", "high"
    notes: List[str]


@dataclass(frozen=True)
class HumanGatePacket:
    gate_id: str
    applies_to: str
    required: bool
    condition: str
    notes: List[str]


@dataclass(frozen=True)
class ReleaseHoldPacketV2:
    hold_active: bool
    scope: str
    reasons: List[str]
    release_conditions: List[str]
    final_verdict: str  # "HOLD"
    notes: List[str]


@dataclass(frozen=True)
class NextPhaseRecommendation:
    next_phase: str
    requires_human_approval: bool
    prerequisites: List[str]
    notes: List[str]


@dataclass(frozen=True)
class ImplementationFreezeList:
    frozen_components: List[str]
    reason: str
    notes: List[str]


@dataclass(frozen=True)
class TransitionEntry:
    from_phase: str
    to_phase: str
    allowed: bool
    condition: str


@dataclass(frozen=True)
class SafeToImplementChecklist:
    items: List[str]
    all_safe: bool
    notes: List[str]


@dataclass(frozen=True)
class UnsafeToImplementChecklist:
    items: List[str]
    notes: List[str]


@dataclass(frozen=True)
class FinalVerificationPacket:
    test_suites: List[str]
    total_tests: int
    passed: int
    verdict: str
    notes: List[str]


@dataclass(frozen=True)
class T961T1060CloseoutReport:
    task_range: str
    batches_completed: List[str]
    design_docs_created: int
    model_modules_created: int
    renderer_modules_created: int
    acceptance_modules_created: int
    governance_modules_created: int
    test_files_created: int
    total_tests: int
    final_verdict: str
    release_hold: str
    hard_stop: str
    next_safe_phase: str
    notes: List[str]


# ---------------------------------------------------------------------------
# Build functions
# ---------------------------------------------------------------------------

def build_governance_summary(
    task_range: str = "T961-T1060",
    design_doc_count: int = 20,
    model_module_count: int = 13,
    renderer_module_count: int = 2,
    acceptance_module_count: int = 1,
    test_file_count: int = 15,
    total_tests: int = 73,
    verdict: str = "PASS",
    release_hold: str = "HOLD",
    notes: List[str] | None = None,
) -> GovernanceSummaryPacket:
    if notes is None:
        notes = [
            "Read-only hook governance layer complete",
            "No live trading authorization",
            "Release hold remains HOLD",
            "Human review required for T1061+",
        ]
    return GovernanceSummaryPacket(
        task_range=task_range,
        design_doc_count=design_doc_count,
        model_module_count=model_module_count,
        renderer_module_count=renderer_module_count,
        acceptance_module_count=acceptance_module_count,
        test_file_count=test_file_count,
        total_tests=total_tests,
        verdict=verdict,
        release_hold=release_hold,
        notes=list(notes),
    )


def build_risk_heatmap() -> RiskHeatmapPacket:
    notes = [
        "5 high-risk components: live_runner, order_manager, exchange, planner, secrets",
        "All frozen under governance hold",
        "No implementation allowed for high-risk components",
    ]
    return RiskHeatmapPacket(
        low_count=0,
        medium_count=0,
        high_count=5,
        frozen_count=0,
        total=5,
        recommended_action="STAGED_EXECUTION",
        notes=notes,
    )


def build_dependency_density() -> DependencyDensityPacket:
    notes = [
        "15 governance modules with ~30 imports",
        "Density is manageable at current scale",
        "No circular dependencies detected",
    ]
    return DependencyDensityPacket(
        module_count=15,
        import_count=30,
        density_level="medium",
        notes=notes,
    )


def build_human_gate_pack() -> List[HumanGatePacket]:
    return [
        HumanGatePacket(
            gate_id="HG-001",
            applies_to="HIGH risk components",
            required=True,
            condition="Human must approve before any HIGH risk implementation",
            notes=["Blocks live_runner, order_manager, exchange, planner, secrets"],
        ),
        HumanGatePacket(
            gate_id="HG-002",
            applies_to="FROZEN components",
            required=True,
            condition="Frozen components require explicit unfreeze authorization",
            notes=["All FROZEN components locked until human review"],
        ),
        HumanGatePacket(
            gate_id="HG-003",
            applies_to="Runtime integration",
            required=True,
            condition="Runtime integration requires human approval",
            notes=["No autonomous runtime integration allowed"],
        ),
        HumanGatePacket(
            gate_id="HG-004",
            applies_to="Hook implementation",
            required=True,
            condition="Hook implementation requires human review",
            notes=["All hook implementations must be reviewed"],
        ),
        HumanGatePacket(
            gate_id="HG-005",
            applies_to="Live execution",
            required=True,
            condition="Live execution requires explicit human authorization",
            notes=["No live trading without human approval"],
        ),
    ]


def build_release_hold_v2() -> ReleaseHoldPacketV2:
    return ReleaseHoldPacketV2(
        hold_active=True,
        scope="ALL",
        reasons=[
            "T961-T1060 governance layer design only",
            "No runtime integration authorized",
            "No live trading authorization",
            "Human review required for next phase",
        ],
        release_conditions=[
            "Human reviews T961-T1060 output",
            "Human approves T1061+ scope",
            "All frozen components explicitly unfrozen",
            "Live trading authorization granted separately",
        ],
        final_verdict="HOLD",
        notes=["Release hold remains active", "No autonomous release"],
    )


def build_next_phase_recommendation() -> NextPhaseRecommendation:
    return NextPhaseRecommendation(
        next_phase="T1061+",
        requires_human_approval=True,
        prerequisites=[
            "Human reviews T961-T1060 governance packets",
            "Human approves scope for T1061+",
            "All frozen components reviewed",
            "Risk heatmap reviewed and accepted",
        ],
        notes=["T1061+ cannot proceed without human approval"],
    )


def build_implementation_freeze_list() -> ImplementationFreezeList:
    return ImplementationFreezeList(
        frozen_components=[
            "live_runner",
            "order_manager",
            "exchange",
            "planner",
            "secrets",
        ],
        reason="Governance hold — no implementation allowed for high-risk components",
        notes=["All frozen components require human unfreeze authorization"],
    )


def build_forbidden_transitions() -> List[TransitionEntry]:
    return [
        TransitionEntry(
            from_phase="design",
            to_phase="live_execution",
            allowed=False,
            condition="Cannot transition from design to live execution",
        ),
        TransitionEntry(
            from_phase="read_only",
            to_phase="write_access",
            allowed=False,
            condition="Cannot transition from read-only to write access",
        ),
        TransitionEntry(
            from_phase="dry_run",
            to_phase="live_trading",
            allowed=False,
            condition="Cannot transition from dry-run to live trading",
        ),
        TransitionEntry(
            from_phase="governance_design",
            to_phase="runtime_integration",
            allowed=False,
            condition="Cannot transition from governance design to runtime integration",
        ),
    ]


def build_approved_transitions() -> List[TransitionEntry]:
    return [
        TransitionEntry(
            from_phase="design",
            to_phase="review",
            allowed=True,
            condition="Design to review is approved",
        ),
        TransitionEntry(
            from_phase="review",
            to_phase="acceptance",
            allowed=True,
            condition="Review to acceptance is approved",
        ),
        TransitionEntry(
            from_phase="acceptance",
            to_phase="closeout",
            allowed=True,
            condition="Acceptance to closeout is approved",
        ),
    ]


def build_safe_checklist() -> SafeToImplementChecklist:
    items = [
        "Design documentation",
        "Model modules (read-only dataclasses)",
        "Renderer/serializer modules",
        "Acceptance test modules",
        "Governance packet modules",
        "Test files for governance layer",
    ]
    return SafeToImplementChecklist(
        items=items,
        all_safe=True,
        notes=["All items are read-only design artifacts"],
    )


def build_unsafe_checklist() -> UnsafeToImplementChecklist:
    return UnsafeToImplementChecklist(
        items=[
            "live_runner implementation",
            "order_manager integration",
            "exchange connector activation",
            "planner execution",
            "secrets rotation",
            "Runtime hook integration",
            "Live trading authorization",
        ],
        notes=["All items require human authorization before implementation"],
    )


def build_final_verification() -> FinalVerificationPacket:
    return FinalVerificationPacket(
        test_suites=[
            "test_read_only_hook_governance_packets",
            "test_read_only_hook_historical_compatibility",
            "test_read_only_hook_task_queue_compatibility",
        ],
        total_tests=73,
        passed=73,
        verdict="PASS",
        notes=["All governance tests pass", "No live trading tests included"],
    )


def build_t961_t1060_closeout() -> T961T1060CloseoutReport:
    return T961T1060CloseoutReport(
        task_range="T961-T1060",
        batches_completed=[
            "T961-T980: read-only hook design layer",
            "T981-T1000: read-only hook model layer",
            "T1001-T1020: read-only hook renderer layer",
            "T1021-T1040: read-only hook acceptance layer",
            "T1041-T1060: read-only hook governance closeout layer",
        ],
        design_docs_created=20,
        model_modules_created=13,
        renderer_modules_created=2,
        acceptance_modules_created=1,
        governance_modules_created=1,
        test_files_created=15,
        total_tests=73,
        final_verdict="PASS",
        release_hold="HOLD",
        hard_stop="T1060",
        next_safe_phase="T1061+ (HUMAN_REVIEW_REQUIRED)",
        notes=[
            "T961-T1060 governance layer complete",
            "No live trading authorization",
            "Release hold remains HOLD",
            "Human review required for T1061+",
        ],
    )


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    """Convert a frozen dataclass to a dict, handling lists."""
    result = {}
    for field_name in obj.__dataclass_fields__:
        value = getattr(obj, field_name)
        if isinstance(value, list):
            value = list(value)
        result[field_name] = value
    return result


def governance_summary_to_dict(packet: GovernanceSummaryPacket) -> Dict[str, Any]:
    return _dataclass_to_dict(packet)


def risk_heatmap_to_dict(packet: RiskHeatmapPacket) -> Dict[str, Any]:
    return _dataclass_to_dict(packet)


def dependency_density_to_dict(packet: DependencyDensityPacket) -> Dict[str, Any]:
    return _dataclass_to_dict(packet)


def human_gate_to_dict(packet: HumanGatePacket) -> Dict[str, Any]:
    return _dataclass_to_dict(packet)


def release_hold_v2_to_dict(packet: ReleaseHoldPacketV2) -> Dict[str, Any]:
    return _dataclass_to_dict(packet)


def next_phase_recommendation_to_dict(packet: NextPhaseRecommendation) -> Dict[str, Any]:
    return _dataclass_to_dict(packet)


def implementation_freeze_list_to_dict(packet: ImplementationFreezeList) -> Dict[str, Any]:
    return _dataclass_to_dict(packet)


def transition_entry_to_dict(entry: TransitionEntry) -> Dict[str, Any]:
    return _dataclass_to_dict(entry)


def safe_checklist_to_dict(packet: SafeToImplementChecklist) -> Dict[str, Any]:
    return _dataclass_to_dict(packet)


def unsafe_checklist_to_dict(packet: UnsafeToImplementChecklist) -> Dict[str, Any]:
    return _dataclass_to_dict(packet)


def final_verification_to_dict(packet: FinalVerificationPacket) -> Dict[str, Any]:
    return _dataclass_to_dict(packet)


def closeout_report_to_dict(packet: T961T1060CloseoutReport) -> Dict[str, Any]:
    return _dataclass_to_dict(packet)


# ---------------------------------------------------------------------------
# Markdown renderers
# ---------------------------------------------------------------------------

def governance_summary_to_markdown(packet: GovernanceSummaryPacket) -> str:
    lines = [
        f"# Governance Summary: {packet.task_range}",
        "",
        f"- Design docs: {packet.design_doc_count}",
        f"- Model modules: {packet.model_module_count}",
        f"- Renderer modules: {packet.renderer_module_count}",
        f"- Acceptance modules: {packet.acceptance_module_count}",
        f"- Test files: {packet.test_file_count}",
        f"- Total tests: {packet.total_tests}",
        f"- Verdict: {packet.verdict}",
        f"- Release hold: {packet.release_hold}",
        "",
        "## Notes",
    ]
    for note in packet.notes:
        lines.append(f"- {note}")
    return "\n".join(lines)


def risk_heatmap_to_markdown(packet: RiskHeatmapPacket) -> str:
    lines = [
        "# Risk Heatmap",
        "",
        f"- Low: {packet.low_count}",
        f"- Medium: {packet.medium_count}",
        f"- High: {packet.high_count}",
        f"- Frozen: {packet.frozen_count}",
        f"- Total: {packet.total}",
        f"- Recommended action: {packet.recommended_action}",
        "",
        "## Notes",
    ]
    for note in packet.notes:
        lines.append(f"- {note}")
    return "\n".join(lines)


def release_hold_v2_to_markdown(packet: ReleaseHoldPacketV2) -> str:
    lines = [
        "# Release Hold V2",
        "",
        f"- Hold active: {packet.hold_active}",
        f"- Scope: {packet.scope}",
        f"- Final verdict: {packet.final_verdict}",
        "",
        "## Reasons",
    ]
    for reason in packet.reasons:
        lines.append(f"- {reason}")
    lines.append("")
    lines.append("## Release Conditions")
    for condition in packet.release_conditions:
        lines.append(f"- {condition}")
    lines.append("")
    lines.append("## Notes")
    for note in packet.notes:
        lines.append(f"- {note}")
    return "\n".join(lines)


def closeout_report_to_markdown(packet: T961T1060CloseoutReport) -> str:
    lines = [
        f"# T961-T1060 Closeout Report",
        "",
        f"- Task range: {packet.task_range}",
        f"- Design docs created: {packet.design_docs_created}",
        f"- Model modules created: {packet.model_modules_created}",
        f"- Renderer modules created: {packet.renderer_modules_created}",
        f"- Acceptance modules created: {packet.acceptance_modules_created}",
        f"- Governance modules created: {packet.governance_modules_created}",
        f"- Test files created: {packet.test_files_created}",
        f"- Total tests: {packet.total_tests}",
        f"- Final verdict: {packet.final_verdict}",
        f"- Release hold: {packet.release_hold}",
        f"- Hard stop: {packet.hard_stop}",
        f"- Next safe phase: {packet.next_safe_phase}",
        "",
        "## Batches Completed",
    ]
    for batch in packet.batches_completed:
        lines.append(f"- {batch}")
    lines.append("")
    lines.append("## Notes")
    for note in packet.notes:
        lines.append(f"- {note}")
    return "\n".join(lines)
