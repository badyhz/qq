"""T30001 — Shadow Pipeline Registry.

Pure deterministic. No I/O. No network.
Registers all SHADOW_PIPELINE scripts and tracks their governance integration.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from core.untracked_runtime_inventory import (
    UntrackedFileRecord,
    build_inventory,
    RELEASE_HOLD_REQUIRED,
)

RELEASE_HOLD_REQUIRED_SPR = "HOLD"

PIPELINE_ROLES = {
    "scripts/run_daily_shadow_scan_pipeline.py": "orchestrator",
    "scripts/run_shadow_sample_collection_pipeline.py": "sample_collector",
    "scripts/run_shadow_universe_collector.py": "universe_collector",
    "scripts/run_right_breakout_param_observation.py": "signal_evaluator",
}

PIPELINE_STAGES = {
    "scripts/run_daily_shadow_scan_pipeline.py": "stage_0_orchestration",
    "scripts/run_shadow_sample_collection_pipeline.py": "stage_1_backfill",
    "scripts/run_shadow_universe_collector.py": "stage_2_universe",
    "scripts/run_right_breakout_param_observation.py": "stage_3_signal_eval",
}


@dataclass(frozen=True)
class ShadowPipelineEntry:
    """Single shadow pipeline registry entry."""
    entry_id: str
    path: str
    pipeline_role: str
    pipeline_stage: str
    risk_category: str
    risk_reason: str
    has_network_calls: bool
    shadow_only: bool
    no_submit: bool
    governance_tracked: bool
    operator_console_connected: bool

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "path": self.path,
            "pipeline_role": self.pipeline_role,
            "pipeline_stage": self.pipeline_stage,
            "risk_category": self.risk_category,
            "risk_reason": self.risk_reason,
            "has_network_calls": self.has_network_calls,
            "shadow_only": self.shadow_only,
            "no_submit": self.no_submit,
            "governance_tracked": self.governance_tracked,
            "operator_console_connected": self.operator_console_connected,
        }


def _safe_id(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__").replace(".", "_")


def build_pipeline_entry(record: UntrackedFileRecord) -> ShadowPipelineEntry:
    """Build a shadow pipeline entry from an inventory record."""
    return ShadowPipelineEntry(
        entry_id=f"spr_{_safe_id(record.path)}",
        path=record.path,
        pipeline_role=PIPELINE_ROLES.get(record.path, "unknown"),
        pipeline_stage=PIPELINE_STAGES.get(record.path, "unknown"),
        risk_category=record.risk_category,
        risk_reason=record.risk_reason,
        has_network_calls=record.has_network_calls,
        shadow_only=True,
        no_submit=not record.has_order_submit,
        governance_tracked=True,
        operator_console_connected=True,
    )


def build_shadow_pipeline_registry(
    release_hold: str = RELEASE_HOLD_REQUIRED_SPR,
) -> list[ShadowPipelineEntry]:
    """Build registry of all shadow pipeline scripts."""
    if release_hold != RELEASE_HOLD_REQUIRED_SPR:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")
    records = build_inventory(release_hold=RELEASE_HOLD_REQUIRED)
    return [
        build_pipeline_entry(r)
        for r in records
        if r.risk_category == "SHADOW_PIPELINE"
    ]


def compute_registry_hash(entries: list[ShadowPipelineEntry]) -> str:
    raw = json.dumps([e.to_dict() for e in entries], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_registry_markdown(entries: list[ShadowPipelineEntry]) -> str:
    lines = [
        "# Shadow Pipeline Registry",
        "",
        f"**Total pipeline scripts:** {len(entries)}",
        "",
        "## Pipeline Stage Order",
        "",
    ]
    sorted_entries = sorted(entries, key=lambda e: e.pipeline_stage)
    for e in sorted_entries:
        lines.append(f"1. **{e.pipeline_stage}** ({e.pipeline_role}): `{e.path}`")

    lines.append("")
    lines.append("## Registry Details")
    lines.append("")

    for e in sorted_entries:
        lines.append(f"### {e.path}")
        lines.append("")
        lines.append(f"- **Role:** {e.pipeline_role}")
        lines.append(f"- **Stage:** {e.pipeline_stage}")
        lines.append(f"- **Risk reason:** {e.risk_reason}")
        lines.append(f"- **Network calls:** {e.has_network_calls}")
        lines.append(f"- **Shadow only:** {e.shadow_only}")
        lines.append(f"- **No submit:** {e.no_submit}")
        lines.append(f"- **Governance tracked:** {e.governance_tracked}")
        lines.append(f"- **Operator console connected:** {e.operator_console_connected}")
        lines.append("")

    return "\n".join(lines)


def render_pipeline_flow_markdown(entries: list[ShadowPipelineEntry]) -> str:
    sorted_entries = sorted(entries, key=lambda e: e.pipeline_stage)
    lines = [
        "# Shadow Pipeline Flow",
        "",
        "```",
    ]
    for i, e in enumerate(sorted_entries):
        prefix = "├── " if i < len(sorted_entries) - 1 else "└── "
        lines.append(f"{prefix}[{e.pipeline_stage}] {e.pipeline_role}")
        lines.append(f"│   └── {e.path}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def write_json(entries: list[ShadowPipelineEntry], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([e.to_dict() for e in entries], indent=2), encoding="utf-8")


def write_manifest(entries: list[ShadowPipelineEntry], out_path, release_hold: str) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    role_counts: dict[str, int] = {}
    for e in entries:
        role_counts[e.pipeline_role] = role_counts.get(e.pipeline_role, 0) + 1
    manifest = {
        "total_pipeline_scripts": len(entries),
        "release_hold": release_hold,
        "registry_hash": compute_registry_hash(entries),
        "all_shadow_only": all(e.shadow_only for e in entries),
        "all_no_submit": all(e.no_submit for e in entries),
        "all_governance_tracked": all(e.governance_tracked for e in entries),
        "all_operator_console_connected": all(e.operator_console_connected for e in entries),
        "role_counts": dict(sorted(role_counts.items())),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(content: str, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
