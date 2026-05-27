"""Read-only hook prompt pack — pure frozen dataclasses, no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ReadOnlyHookPromptPack:
    pack_id: str
    task_range: str
    prompt_text: str
    required_docs: List[str]
    safety_warnings: List[str]
    hard_stop: str


def build_read_only_hook_prompt_pack(task_range: str = "T981-T1000") -> ReadOnlyHookPromptPack:
    return ReadOnlyHookPromptPack(
        pack_id=f"prompt_pack_{task_range.replace('-', '_').lower()}",
        task_range=task_range,
        prompt_text=(
            f"Implement read-only hook contract model layer ({task_range}). "
            "All modules must use frozen dataclasses. No I/O, no network, no timestamps, no random. "
            "Pure functions only. Every dataclass must have a *_to_dict() serializer."
        ),
        required_docs=[
            "PROJECT_STATE.md",
            "TASKS.md",
            "acceptance.json",
            "feature_list.json",
            "AGENT_RULES.md",
        ],
        safety_warnings=[
            "NO real orders — read-only hooks must never trigger execution",
            "NO hardcoded secrets — sanitize all payloads",
            "NO mutable state — all dataclasses frozen",
            "NO side effects — side_effects_declared must be empty",
            "All invariants must pass before output is valid",
        ],
        hard_stop=(
            "If any invariant check fails, the hook output must be status 'denied' or 'error'. "
            "Never return 'success' with failed invariants."
        ),
    )


def prompt_pack_to_dict(pack: ReadOnlyHookPromptPack) -> dict:
    return {
        "pack_id": pack.pack_id,
        "task_range": pack.task_range,
        "prompt_text": pack.prompt_text,
        "required_docs": list(pack.required_docs),
        "safety_warnings": list(pack.safety_warnings),
        "hard_stop": pack.hard_stop,
    }
