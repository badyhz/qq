"""PRD agent prompt generator — generates short agent prompts from PRD task ranges.

T868. Pure deterministic, no I/O, no timestamps, no random.
"""

from dataclasses import dataclass
from typing import Dict, List

from core.prd_task_model import PrdTask


# --- Dataclass ---


@dataclass(frozen=True)
class PrdAgentPrompt:
    """Frozen dataclass for agent prompt output."""
    task_range: str
    prompt_text: str
    required_docs: List[str]
    hard_stop_task_id: str
    safety_warnings: List[str]
    notes: List[str]


# --- Helpers ---


def _build_task_summary(tasks: List[PrdTask]) -> str:
    """Build task summary lines."""
    lines = []
    for task in tasks:
        lines.append(f"- {task.task_id}: {task.title} [{task.status}]")
    return "\n".join(lines)


def _build_acceptance_section(tasks: List[PrdTask]) -> str:
    """Build acceptance commands section."""
    lines = []
    seen = set()
    for task in tasks:
        for cmd in task.acceptance_commands:
            if cmd not in seen:
                seen.add(cmd)
                lines.append(f"- `{cmd}`")
    return "\n".join(lines)


def _build_allowed_files_section(tasks: List[PrdTask]) -> str:
    """Build allowed files section."""
    lines = []
    seen = set()
    for task in tasks:
        for f in task.allowed_files:
            if f not in seen:
                seen.add(f)
                lines.append(f"- {f}")
    return "\n".join(lines)


# --- Core function ---


def generate_agent_prompt_for_task_range(
    tasks: List[PrdTask],
    start_task_id: str,
    end_task_id: str,
    required_docs: List[str],
) -> PrdAgentPrompt:
    """Generate agent prompt for a task range.

    Pure, deterministic. No I/O, no timestamps, no random.
    """
    # Build prompt text
    lines: List[str] = []
    lines.append("# Agent Prompt")
    lines.append("")
    lines.append("## Mode")
    lines.append("Use Caveman / terse engineering mode.")
    lines.append("")
    lines.append("## Output Format")
    lines.append("Output only: FILES / TESTS / COMMITS / RESULT / NOTES")
    lines.append("")
    lines.append("## Required Docs")
    for doc in required_docs:
        lines.append(f"- Read {doc} before starting.")
    lines.append("")
    lines.append("## Task Range")
    lines.append(f"Execute only: {start_task_id} .. {end_task_id}")
    lines.append("")
    lines.append("## Tasks")
    lines.append(_build_task_summary(tasks))
    lines.append("")
    lines.append("## Allowed Files")
    lines.append(_build_allowed_files_section(tasks))
    lines.append("")
    lines.append("## Acceptance Commands")
    lines.append(_build_acceptance_section(tasks))
    lines.append("")
    lines.append("## Safety Rules")
    lines.append("- Do not modify frozen modules.")
    lines.append("- Do not touch live trading / submit / planner / exchange / secrets / runtime execution.")
    lines.append("- Follow acceptance rules.")
    lines.append("- Commit per task.")
    lines.append("")
    lines.append("## Hard Stop")
    lines.append(f"HARD STOP after {end_task_id}. Do not continue beyond {end_task_id}.")

    prompt_text = "\n".join(lines)

    # Safety warnings
    safety_warnings = [
        "Do not modify frozen modules.",
        "Do not touch live trading / submit / planner / exchange / secrets / runtime execution.",
        f"HARD STOP after {end_task_id}. Do not continue beyond {end_task_id}.",
    ]

    # Notes from tasks
    notes: List[str] = []
    seen_notes = set()
    for task in tasks:
        for note in task.notes:
            if note not in seen_notes:
                seen_notes.add(note)
                notes.append(note)

    return PrdAgentPrompt(
        task_range=f"{start_task_id}..{end_task_id}",
        prompt_text=prompt_text,
        required_docs=list(required_docs),
        hard_stop_task_id=end_task_id,
        safety_warnings=safety_warnings,
        notes=notes,
    )


# --- Serializers ---


def prd_agent_prompt_to_dict(prompt: PrdAgentPrompt) -> Dict:
    """Convert PrdAgentPrompt to dict."""
    return {
        "task_range": prompt.task_range,
        "prompt_text": prompt.prompt_text,
        "required_docs": list(prompt.required_docs),
        "hard_stop_task_id": prompt.hard_stop_task_id,
        "safety_warnings": list(prompt.safety_warnings),
        "notes": list(prompt.notes),
    }


def prd_agent_prompt_to_markdown(prompt: PrdAgentPrompt) -> str:
    """Convert PrdAgentPrompt to markdown string."""
    lines: List[str] = []
    lines.append(f"# Agent Prompt: {prompt.task_range}")
    lines.append("")
    lines.append(f"**Hard stop:** {prompt.hard_stop_task_id}")
    lines.append("")
    if prompt.required_docs:
        lines.append("## Required Docs")
        for doc in prompt.required_docs:
            lines.append(f"- {doc}")
        lines.append("")
    if prompt.safety_warnings:
        lines.append("## Safety Warnings")
        for warning in prompt.safety_warnings:
            lines.append(f"- {warning}")
        lines.append("")
    lines.append("## Prompt")
    lines.append("")
    lines.append(prompt.prompt_text)
    if prompt.notes:
        lines.append("")
        lines.append("## Notes")
        for note in prompt.notes:
            lines.append(f"- {note}")
    return "\n".join(lines)
