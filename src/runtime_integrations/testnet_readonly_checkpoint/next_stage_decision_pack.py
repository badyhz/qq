"""Next stage decision pack: candidate routes for next phase, not executed."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class StageOption:
    option_id: str
    title: str
    recommended_when: str
    risk_level: str
    allowed_actions: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    requires_human_approval: bool
    def to_dict(self) -> dict:
        return {"option_id": self.option_id, "title": self.title,
                "recommended_when": self.recommended_when, "risk_level": self.risk_level,
                "allowed_actions": list(self.allowed_actions),
                "forbidden_actions": list(self.forbidden_actions),
                "requires_human_approval": self.requires_human_approval}


@dataclass(frozen=True)
class NextStageDecisionPack:
    pack_id: str
    created_at: str
    recommended_next: str
    recommendation_reason: str
    options: tuple[StageOption, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"pack_id": self.pack_id, "created_at": self.created_at,
                "recommended_next": self.recommended_next,
                "recommendation_reason": self.recommendation_reason,
                "options": [o.to_dict() for o in self.options],
                "final_verdict": self.final_verdict}


OPTIONS = (
    StageOption("OPTION_A_CONTINUE_READONLY_NETWORK_ENABLEMENT_DESIGN",
        "Continue read-only network enablement design",
        "When human approves moving to real readonly network phase",
        "MEDIUM",
        ("design_readonly_adapter", "plan_network_policy", "draft_credential_scope"),
        ("real_network_call", "real_credential_load", "order_submission", "order_cancellation"),
        True),
    StageOption("OPTION_B_BUILD_ADAPTER_BLUEPRINT_ONLY_NO_NETWORK",
        "Build adapter blueprint without network",
        "When more design depth is needed before any network enablement",
        "LOW",
        ("adapter_interface_design", "mock_adapter_refinement", "test_harness_expansion"),
        ("real_network_call", "real_credential_load", "order_submission", "readonly_network_enablement"),
        False),
    StageOption("OPTION_C_PAUSE_EXTERNAL_TESTNET_AND_RETURN_TO_STRATEGY_SCANNER",
        "Pause external testnet work and return to strategy scanner",
        "When strategy scanner needs attention before continuing governance chain",
        "LOW",
        ("strategy_scanner_maintenance", "signal_engine_review", "risk_manager_audit"),
        ("real_network_call", "real_credential_load", "order_submission", "governance_chain_progression"),
        False),
    StageOption("OPTION_D_ARCHIVE_CURRENT_CHAIN_AND_WAIT_FOR_HUMAN_APPROVAL",
        "Archive current chain and wait for human approval",
        "When governance chain is complete and next step requires human decision",
        "LOW",
        ("archive_documentation", "handoff_report_generation", "human_review_queue"),
        ("real_network_call", "real_credential_load", "order_submission", "automatic_progression"),
        True),
)


def create_pack() -> NextStageDecisionPack:
    return NextStageDecisionPack(
        pack_id=f"NSD_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        recommended_next="OPTION_D_ARCHIVE_CURRENT_CHAIN_AND_WAIT_FOR_HUMAN_APPROVAL",
        recommendation_reason="T155001-T335000 completed mock/governance/read-only design chain. Next step into real network enablement requires human confirmation. Should not auto-enable real readonly network.",
        options=OPTIONS,
        final_verdict="READONLY_NEXT_STAGE_DECISION_PACK_READY|RECOMMENDED_OPTION_D|HUMAN_APPROVAL_REQUIRED",
    )


def write_pack(pack: NextStageDecisionPack, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pack.to_dict(), indent=2), encoding="utf-8")


def render_report(pack: NextStageDecisionPack) -> str:
    lines = ["# Next Stage Decision Pack", "",
        f"**pack_id={pack.pack_id}**",
        f"**recommended_next={pack.recommended_next}**",
        f"**reason={pack.recommendation_reason}**", "",
        "## Options", "",
        "| ID | Title | Risk | Human Approval |",
        "|----|-------|------|:---:|"]
    for o in pack.options:
        lines.append(f"| {o.option_id} | {o.title} | {o.risk_level} | {'Y' if o.requires_human_approval else 'N'} |")
    lines.extend(["", "## Conclusion", "",
        "READONLY_NEXT_STAGE_DECISION_PACK_READY",
        "RECOMMENDED_OPTION_D",
        "HUMAN_APPROVAL_REQUIRED",
        "REAL_NETWORK_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
