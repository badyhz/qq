"""T916 — 500 backlog closeout.

Aggregates all PRD 500 planning artifacts into a single closeout report.
Pure deterministic. No I/O. No timestamps. No random.
"""

from dataclasses import dataclass
from typing import Dict, List

from core.prd_500_backlog_materializer import (
    materialize_prd_500_backlog,
    summarize_prd_500_backlog,
)
from core.prd_500_backlog_milestone_map import (
    build_prd_500_milestone_map,
    summarize_milestone_map,
)
from core.prd_500_backlog_wave_map import (
    build_prd_500_wave_map,
    summarize_wave_map,
)
from core.prd_500_backlog_batch_map import (
    build_prd_500_batch_map,
    summarize_batch_map,
)
from core.prd_500_backlog_prompt_packs import (
    build_prd_500_prompt_packs,
    summarize_prompt_packs,
)
from core.prd_500_backlog_validator import validate_prd_500_backlog
from core.prd_500_backlog_release_hold import build_prd_500_backlog_release_hold


# --- Constants ---

_TASK_RANGE = "T901-T960"
_SOURCE_TASK_COUNT = 16  # T901-T916 source modules
_HARD_STOP = "T960"
_NEXT_SAFE_PHASE = "T961-T980 requires human approval"
_FINAL_STATUS_ACCEPT = frozenset({"PASS", "WARN"})


# --- Dataclass ---


@dataclass(frozen=True)
class Prd500BacklogCloseout:
    task_range: str
    source_task_count: int
    materialized_item_count: int
    milestone_count: int
    wave_count: int
    batch_count: int
    prompt_pack_count: int
    validation_verdict: str
    release_hold_verdict: str
    final_status: str
    hard_stop: str
    next_safe_phase: str
    notes: List[str]


# --- Build ---


def build_prd_500_backlog_closeout() -> Prd500BacklogCloseout:
    """Materialize backlog, build all maps, validate, return closeout.

    Pure deterministic. No I/O. No timestamps. No random.
    """
    # 1. Materialize
    backlog = materialize_prd_500_backlog()
    backlog_summary = summarize_prd_500_backlog(backlog)

    # 2. Maps
    milestones = build_prd_500_milestone_map(backlog)
    milestone_summary = summarize_milestone_map(milestones)

    waves = build_prd_500_wave_map(backlog)
    wave_summary = summarize_wave_map(waves)

    batches = build_prd_500_batch_map(backlog)
    batch_summary = summarize_batch_map(batches)

    packs = build_prd_500_prompt_packs(backlog)
    pack_summary = summarize_prompt_packs(packs)

    # 3. Validate
    validation = validate_prd_500_backlog(backlog)

    # 4. Release hold
    release_hold = build_prd_500_backlog_release_hold()

    # 5. Final status
    validation_verdict = validation.final_verdict
    release_hold_verdict = release_hold.final_verdict

    if validation_verdict in _FINAL_STATUS_ACCEPT:
        final_status = validation_verdict
    else:
        final_status = "PARTIAL"

    # 6. Notes
    notes: List[str] = []
    notes.append(f"materialized items: {backlog_summary.get('total_items', len(backlog.items))}")
    notes.append(f"milestones: {milestone_summary.get('milestone_count', len(milestones))}")
    notes.append(f"waves: {wave_summary.get('wave_count', len(waves))}")
    notes.append(f"batches: {batch_summary.get('total_batches', len(batches))}")
    notes.append(f"prompt packs: {pack_summary.get('total_packs', len(packs))}")

    if validation.issue_count > 0:
        notes.append(f"validation issues: {validation.issue_count}")

    if release_hold.hold_active:
        notes.append("release hold ACTIVE — no execution without human approval")

    return Prd500BacklogCloseout(
        task_range=_TASK_RANGE,
        source_task_count=_SOURCE_TASK_COUNT,
        materialized_item_count=backlog_summary.get("total_items", len(backlog.items)),
        milestone_count=milestone_summary.get("milestone_count", len(milestones)),
        wave_count=wave_summary.get("wave_count", len(waves)),
        batch_count=batch_summary.get("total_batches", len(batches)),
        prompt_pack_count=pack_summary.get("total_packs", len(packs)),
        validation_verdict=validation_verdict,
        release_hold_verdict=release_hold_verdict,
        final_status=final_status,
        hard_stop=_HARD_STOP,
        next_safe_phase=_NEXT_SAFE_PHASE,
        notes=tuple(notes),  # frozen needs tuple
    )


# --- Serializers ---


def closeout_to_dict(closeout: Prd500BacklogCloseout) -> Dict[str, object]:
    """Stable dict with sorted keys."""
    return {
        "task_range": closeout.task_range,
        "source_task_count": closeout.source_task_count,
        "materialized_item_count": closeout.materialized_item_count,
        "milestone_count": closeout.milestone_count,
        "wave_count": closeout.wave_count,
        "batch_count": closeout.batch_count,
        "prompt_pack_count": closeout.prompt_pack_count,
        "validation_verdict": closeout.validation_verdict,
        "release_hold_verdict": closeout.release_hold_verdict,
        "final_status": closeout.final_status,
        "hard_stop": closeout.hard_stop,
        "next_safe_phase": closeout.next_safe_phase,
        "notes": list(closeout.notes),
    }


def closeout_to_markdown(closeout: Prd500BacklogCloseout) -> str:
    """Render closeout as markdown."""
    lines = [
        "# PRD 500 Backlog Closeout",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Task Range | {closeout.task_range} |",
        f"| Source Task Count | {closeout.source_task_count} |",
        f"| Materialized Items | {closeout.materialized_item_count} |",
        f"| Milestones | {closeout.milestone_count} |",
        f"| Waves | {closeout.wave_count} |",
        f"| Batches | {closeout.batch_count} |",
        f"| Prompt Packs | {closeout.prompt_pack_count} |",
        f"| Validation Verdict | {closeout.validation_verdict} |",
        f"| Release Hold Verdict | {closeout.release_hold_verdict} |",
        f"| Final Status | {closeout.final_status} |",
        f"| Hard Stop | {closeout.hard_stop} |",
        f"| Next Safe Phase | {closeout.next_safe_phase} |",
        "",
        "## Notes",
        "",
    ]
    for note in closeout.notes:
        lines.append(f"- {note}")
    return "\n".join(lines)
