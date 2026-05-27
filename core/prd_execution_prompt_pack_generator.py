"""PRD execution prompt pack generator — generates agent prompt packs from backlog data.

T894. Pure deterministic, no I/O, no timestamps, no random.
Groups backlog items by milestone/wave into prompt packs for batch execution.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from core.prd_backlog_schema import PrdBacklogItem


# --- Dataclasses ---


@dataclass(frozen=True)
class PrdExecutionPrompt:
    """Frozen dataclass for a single execution prompt."""
    prompt_id: str
    task_id: str
    title: str
    risk_level: str
    allowed_files: List[str]
    acceptance_commands: List[str]
    prompt_text: str
    notes: List[str]


@dataclass(frozen=True)
class PrdExecutionPromptPack:
    """Frozen dataclass for a pack of execution prompts grouped by milestone/wave."""
    pack_id: str
    milestone_id: str
    wave_id: str
    prompts: List[PrdExecutionPrompt]
    total_prompts: int
    notes: List[str]


# --- Helpers ---


def _build_prompt_text(item: PrdBacklogItem) -> str:
    """Build prompt text for a single backlog item."""
    lines: List[str] = []
    lines.append(f"# Execute: {item.task_id}")
    lines.append("")
    lines.append(f"**Title:** {item.title}")
    lines.append(f"**Risk level:** {item.risk_level}")
    lines.append("")
    if item.allowed_file_patterns:
        lines.append("## Allowed Files")
        for f in item.allowed_file_patterns:
            lines.append(f"- {f}")
        lines.append("")
    if item.forbidden_file_patterns:
        lines.append("## Forbidden Files")
        for f in item.forbidden_file_patterns:
            lines.append(f"- {f}")
        lines.append("")
    if item.dependencies:
        lines.append("## Dependencies")
        for dep in item.dependencies:
            lines.append(f"- {dep}")
        lines.append("")
    if item.acceptance_command_ids:
        lines.append("## Acceptance Commands")
        for cmd in item.acceptance_command_ids:
            lines.append(f"- `{cmd}`")
        lines.append("")
    lines.append("## Safety Rules")
    lines.append("- Do not modify frozen modules.")
    lines.append("- Do not touch live trading / secrets / runtime execution.")
    lines.append("- Follow acceptance rules.")
    lines.append("- Commit per task.")
    return "\n".join(lines)


def _collect_unique_notes(items: List[PrdBacklogItem]) -> List[str]:
    """Collect unique notes from items preserving order."""
    seen: set = set()
    result: List[str] = []
    for item in items:
        for note in item.notes:
            if note not in seen:
                seen.add(note)
                result.append(note)
    return result


# --- Core functions ---


def generate_prompt_for_item(item: PrdBacklogItem) -> PrdExecutionPrompt:
    """Generate a single execution prompt from a backlog item.

    Pure, deterministic. No I/O, no timestamps, no random.
    """
    prompt_text = _build_prompt_text(item)
    return PrdExecutionPrompt(
        prompt_id=f"EP-{item.task_id}",
        task_id=item.task_id,
        title=item.title,
        risk_level=item.risk_level,
        allowed_files=list(item.allowed_file_patterns),
        acceptance_commands=list(item.acceptance_command_ids),
        prompt_text=prompt_text,
        notes=list(item.notes),
    )


def generate_prompt_pack_for_milestone(
    items: List[PrdBacklogItem],
    milestone_id: str,
) -> PrdExecutionPromptPack:
    """Generate a prompt pack for a milestone from backlog items.

    All items must share the same milestone_id. Items are grouped by wave_id
    (first wave_id found determines the pack's wave_id; mixed waves use 'mixed').

    Pure, deterministic. No I/O, no timestamps, no random.
    """
    milestone_items = [i for i in items if i.milestone_id == milestone_id]
    if not milestone_items:
        return PrdExecutionPromptPack(
            pack_id=f"PACK-{milestone_id}",
            milestone_id=milestone_id,
            wave_id="",
            prompts=[],
            total_prompts=0,
            notes=[],
        )

    # Determine wave_id: use 'mixed' if items span multiple waves
    wave_ids = {i.wave_id for i in milestone_items}
    wave_id = milestone_items[0].wave_id if len(wave_ids) == 1 else "mixed"

    prompts = [generate_prompt_for_item(i) for i in milestone_items]
    notes = _collect_unique_notes(milestone_items)

    return PrdExecutionPromptPack(
        pack_id=f"PACK-{milestone_id}",
        milestone_id=milestone_id,
        wave_id=wave_id,
        prompts=prompts,
        total_prompts=len(prompts),
        notes=notes,
    )


def generate_all_prompt_packs(
    items: List[PrdBacklogItem],
) -> List[PrdExecutionPromptPack]:
    """Generate prompt packs for all milestones found in backlog items.

    Groups items by milestone_id, then generates a pack per milestone.
    Order follows first appearance of each milestone_id.

    Pure, deterministic. No I/O, no timestamps, no random.
    """
    seen: set = set()
    milestone_ids: List[str] = []
    for item in items:
        if item.milestone_id not in seen:
            seen.add(item.milestone_id)
            milestone_ids.append(item.milestone_id)
    return [
        generate_prompt_pack_for_milestone(items, mid)
        for mid in milestone_ids
    ]


# --- Serializers ---


def prompt_to_dict(prompt: PrdExecutionPrompt) -> Dict[str, Any]:
    """Convert PrdExecutionPrompt to dict."""
    return {
        "prompt_id": prompt.prompt_id,
        "task_id": prompt.task_id,
        "title": prompt.title,
        "risk_level": prompt.risk_level,
        "allowed_files": list(prompt.allowed_files),
        "acceptance_commands": list(prompt.acceptance_commands),
        "prompt_text": prompt.prompt_text,
        "notes": list(prompt.notes),
    }


def prompt_pack_to_dict(pack: PrdExecutionPromptPack) -> Dict[str, Any]:
    """Convert PrdExecutionPromptPack to dict."""
    return {
        "pack_id": pack.pack_id,
        "milestone_id": pack.milestone_id,
        "wave_id": pack.wave_id,
        "prompts": [prompt_to_dict(p) for p in pack.prompts],
        "total_prompts": pack.total_prompts,
        "notes": list(pack.notes),
    }


def prompt_pack_to_markdown(pack: PrdExecutionPromptPack) -> str:
    """Convert PrdExecutionPromptPack to markdown string."""
    lines: List[str] = []
    lines.append(f"# Prompt Pack: {pack.pack_id}")
    lines.append("")
    lines.append(f"**Milestone:** {pack.milestone_id}")
    lines.append(f"**Wave:** {pack.wave_id}")
    lines.append(f"**Total prompts:** {pack.total_prompts}")
    lines.append("")
    if pack.notes:
        lines.append("## Pack Notes")
        for note in pack.notes:
            lines.append(f"- {note}")
        lines.append("")
    for prompt in pack.prompts:
        lines.append(f"## {prompt.prompt_id}: {prompt.title}")
        lines.append("")
        lines.append(f"- **Task:** {prompt.task_id}")
        lines.append(f"- **Risk:** {prompt.risk_level}")
        if prompt.allowed_files:
            lines.append(f"- **Allowed files:** {', '.join(prompt.allowed_files)}")
        if prompt.acceptance_commands:
            lines.append("- **Acceptance commands:**")
            for cmd in prompt.acceptance_commands:
                lines.append(f"  - `{cmd}`")
        lines.append("")
        lines.append(prompt.prompt_text)
        lines.append("")
        if prompt.notes:
            lines.append("**Prompt notes:**")
            for note in prompt.notes:
                lines.append(f"- {note}")
            lines.append("")
    return "\n".join(lines)
