"""T27001 — Research Artifact Registry.

Pure deterministic. No I/O. No network.
Registers all SAFE_RESEARCH, SAFE_IMPORTER, and SAFE_REPORT scripts
as governance-tracked research artifacts.
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

RELEASE_HOLD_REQUIRED_REG = "HOLD"

SAFE_CATEGORIES = ("SAFE_RESEARCH", "SAFE_IMPORTER", "SAFE_REPORT")

ARTIFACT_TYPES = {
    "SAFE_RESEARCH": "research_scanner",
    "SAFE_IMPORTER": "data_source_adapter",
    "SAFE_REPORT": "verification_report",
}

INTEGRATION_PATHS = {
    "SAFE_RESEARCH": "strategy_registry",
    "SAFE_IMPORTER": "alert_center",
    "SAFE_REPORT": "operator_console",
}


@dataclass(frozen=True)
class ResearchArtifact:
    """Single registered research artifact."""
    artifact_id: str
    path: str
    artifact_type: str
    risk_category: str
    risk_reason: str
    integration_target: str
    has_network_calls: bool
    has_api_keys: bool
    governance_tracked: bool
    dry_run_compatible: bool
    ready_for_integration: bool

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "path": self.path,
            "artifact_type": self.artifact_type,
            "risk_category": self.risk_category,
            "risk_reason": self.risk_reason,
            "integration_target": self.integration_target,
            "has_network_calls": self.has_network_calls,
            "has_api_keys": self.has_api_keys,
            "governance_tracked": self.governance_tracked,
            "dry_run_compatible": self.dry_run_compatible,
            "ready_for_integration": self.ready_for_integration,
        }


def _safe_id(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__").replace(".", "_")


def build_artifact(record: UntrackedFileRecord) -> ResearchArtifact:
    """Build a research artifact from an inventory record."""
    return ResearchArtifact(
        artifact_id=f"art_{_safe_id(record.path)}",
        path=record.path,
        artifact_type=ARTIFACT_TYPES.get(record.risk_category, "unknown"),
        risk_category=record.risk_category,
        risk_reason=record.risk_reason,
        integration_target=INTEGRATION_PATHS.get(record.risk_category, "unknown"),
        has_network_calls=record.has_network_calls,
        has_api_keys=record.has_api_keys,
        governance_tracked=True,
        dry_run_compatible=not record.has_network_calls,
        ready_for_integration=record.risk_category in SAFE_CATEGORIES,
    )


def build_artifact_registry(
    release_hold: str = RELEASE_HOLD_REQUIRED_REG,
) -> list[ResearchArtifact]:
    """Build registry of all safe research artifacts."""
    if release_hold != RELEASE_HOLD_REQUIRED_REG:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")
    records = build_inventory(release_hold=RELEASE_HOLD_REQUIRED)
    return [
        build_artifact(r)
        for r in records
        if r.risk_category in SAFE_CATEGORIES
    ]


def compute_registry_hash(artifacts: list[ResearchArtifact]) -> str:
    raw = json.dumps([a.to_dict() for a in artifacts], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_registry_markdown(artifacts: list[ResearchArtifact]) -> str:
    lines = [
        "# Research Artifact Registry",
        "",
        f"**Total artifacts:** {len(artifacts)}",
        "",
        "## By Type",
        "",
    ]
    type_counts: dict[str, int] = {}
    for a in artifacts:
        type_counts[a.artifact_type] = type_counts.get(a.artifact_type, 0) + 1
    for t, count in sorted(type_counts.items()):
        lines.append(f"- **{t}:** {count}")

    lines.append("")
    lines.append("## By Integration Target")
    lines.append("")
    target_counts: dict[str, int] = {}
    for a in artifacts:
        target_counts[a.integration_target] = target_counts.get(a.integration_target, 0) + 1
    for t, count in sorted(target_counts.items()):
        lines.append(f"- **{t}:** {count}")

    lines.append("")
    lines.append("## Artifact Details")
    lines.append("")

    for a in artifacts:
        lines.append(f"### {a.path}")
        lines.append("")
        lines.append(f"- **Type:** {a.artifact_type}")
        lines.append(f"- **Category:** {a.risk_category}")
        lines.append(f"- **Reason:** {a.risk_reason}")
        lines.append(f"- **Integration target:** {a.integration_target}")
        lines.append(f"- **Network calls:** {a.has_network_calls}")
        lines.append(f"- **API keys:** {a.has_api_keys}")
        lines.append(f"- **Governance tracked:** {a.governance_tracked}")
        lines.append(f"- **Dry-run compatible:** {a.dry_run_compatible}")
        lines.append(f"- **Ready for integration:** {a.ready_for_integration}")
        lines.append("")

    return "\n".join(lines)


def render_integration_matrix_markdown(artifacts: list[ResearchArtifact]) -> str:
    lines = [
        "# Research Artifact Integration Matrix",
        "",
        "| File | Type | Target | Network | Dry-run OK | Ready |",
        "|------|------|--------|---------|------------|-------|",
    ]
    for a in artifacts:
        lines.append(
            f"| {a.path} | {a.artifact_type} | {a.integration_target} "
            f"| {a.has_network_calls} | {a.dry_run_compatible} | {a.ready_for_integration} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_json(artifacts: list[ResearchArtifact], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([a.to_dict() for a in artifacts], indent=2), encoding="utf-8")


def write_manifest(artifacts: list[ResearchArtifact], out_path, release_hold: str) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    type_counts: dict[str, int] = {}
    for a in artifacts:
        type_counts[a.artifact_type] = type_counts.get(a.artifact_type, 0) + 1
    target_counts: dict[str, int] = {}
    for a in artifacts:
        target_counts[a.integration_target] = target_counts.get(a.integration_target, 0) + 1
    manifest = {
        "total_artifacts": len(artifacts),
        "type_counts": dict(sorted(type_counts.items())),
        "target_counts": dict(sorted(target_counts.items())),
        "release_hold": release_hold,
        "registry_hash": compute_registry_hash(artifacts),
        "all_governance_tracked": all(a.governance_tracked for a in artifacts),
        "all_ready_for_integration": all(a.ready_for_integration for a in artifacts),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(content: str, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
