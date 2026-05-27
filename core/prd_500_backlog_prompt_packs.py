"""T911 — 500 backlog prompt packs.

Pure deterministic. No I/O. No timestamps. No random.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem

DEFAULT_REQUIRED_DOCS: List[str] = [
    "docs/dev_prd/agent_execution_protocol.md",
    "docs/dev_prd/runtime_governance_safety_boundaries.md",
]

SAFETY_WARNINGS: List[str] = [
    "No live trading authorization",
    "No real order placement",
    "No secrets access",
    "No planner autonomous execution",
]

PACK_SIZE: int = 25


@dataclass(frozen=True)
class Prd500PromptPack:
    pack_id: str
    window_id: str
    task_range: str
    prompt_text: str
    hard_stop_task_id: str
    required_docs: List[str]
    safety_warnings: List[str]
    notes: List[str]


def _build_prompt_text(
    start: str,
    end: str,
    hard_stop: str,
    required_docs: List[str],
) -> str:
    docs_list = "\n".join(f"  - {d}" for d in required_docs)
    return (
        "Use Caveman / terse engineering mode.\n"
        "Output only FILES / TESTS / COMMITS / RESULT / NOTES.\n"
        f"Read required docs:\n{docs_list}\n"
        f"Execute only task range: {start} to {end}.\n"
        f"Hard stop after {hard_stop}.\n"
        "Do not touch live trading / submit / planner / exchange / secrets / runtime execution.\n"
        "Do not continue beyond hard stop."
    )


def build_prd_500_prompt_packs(
    backlog: PrdBacklog,
    required_docs: Optional[List[str]] = None,
) -> List[Prd500PromptPack]:
    """Split backlog into prompt packs of PACK_SIZE tasks each."""
    docs = list(required_docs) if required_docs is not None else list(DEFAULT_REQUIRED_DOCS)
    items = list(backlog.items)
    packs: List[Prd500PromptPack] = []
    for i in range(0, len(items), PACK_SIZE):
        chunk = items[i : i + PACK_SIZE]
        start_id = chunk[0].task_id
        end_id = chunk[-1].task_id
        hard_stop = end_id
        pack_idx = i // PACK_SIZE
        pack_id = f"prompt-pack-{pack_idx:04d}"
        window_id = f"window-{pack_idx:04d}"
        task_range = f"{start_id}..{end_id}"
        prompt_text = _build_prompt_text(start_id, end_id, hard_stop, docs)
        packs.append(
            Prd500PromptPack(
                pack_id=pack_id,
                window_id=window_id,
                task_range=task_range,
                prompt_text=prompt_text,
                hard_stop_task_id=hard_stop,
                required_docs=tuple(docs),
                safety_warnings=tuple(SAFETY_WARNINGS),
                notes=tuple(),
            )
        )
    return packs


def prompt_packs_to_dict(pack: Prd500PromptPack) -> Dict[str, Any]:
    return {
        "pack_id": pack.pack_id,
        "window_id": pack.window_id,
        "task_range": pack.task_range,
        "prompt_text": pack.prompt_text,
        "hard_stop_task_id": pack.hard_stop_task_id,
        "required_docs": list(pack.required_docs),
        "safety_warnings": list(pack.safety_warnings),
        "notes": list(pack.notes),
    }


def prompt_packs_to_markdown(pack: Prd500PromptPack) -> str:
    lines: List[str] = []
    lines.append(f"# {pack.pack_id}")
    lines.append("")
    lines.append(f"- **Window:** {pack.window_id}")
    lines.append(f"- **Task range:** {pack.task_range}")
    lines.append(f"- **Hard stop:** {pack.hard_stop_task_id}")
    lines.append("")
    lines.append("## Prompt")
    lines.append("")
    lines.append("```")
    lines.append(pack.prompt_text)
    lines.append("```")
    lines.append("")
    lines.append("## Required docs")
    for d in pack.required_docs:
        lines.append(f"- {d}")
    lines.append("")
    lines.append("## Safety warnings")
    for w in pack.safety_warnings:
        lines.append(f"- **{w}**")
    if pack.notes:
        lines.append("")
        lines.append("## Notes")
        for n in pack.notes:
            lines.append(f"- {n}")
    return "\n".join(lines)


def summarize_prompt_packs(packs: List[Prd500PromptPack]) -> Dict[str, Any]:
    total = len(packs)
    all_warnings: Dict[str, int] = {}
    for p in packs:
        for w in p.safety_warnings:
            all_warnings[w] = all_warnings.get(w, 0) + 1
    return {
        "total_packs": total,
        "pack_ids": [p.pack_id for p in packs],
        "task_ranges": [p.task_range for p in packs],
        "safety_warnings": all_warnings,
    }
