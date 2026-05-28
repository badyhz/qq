"""Offline research result catalog.

Scans explicit offline output dirs for research artifacts.
Never imports, executes, stages, or modifies any file.
Never scans repo frozen files unless in explicit output dir.

release_hold = HOLD
advisory_only = True
no_live / no_submit / no_exchange / no_network = True
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
from dataclasses import dataclass, field
from typing import Any

RELEASE_HOLD_REQUIRED = "HOLD"

# Explicit offline output dirs to scan
DEFAULT_SCAN_DIRS = [
    "/tmp/multi_strategy_research_workbench",
    "/tmp/multi_strategy_research_quality_gate",
    "/tmp/research_artifact_browser",
    "/tmp/research_comparison_analytics",
    "/tmp/research_human_review_packet",
    "/tmp/offline_research_operator_bundle",
    "/tmp/offline_research_experiment_library_validation",
    "/tmp/offline_research_governance_validation",
    "/tmp/frozen_inventory_review",
    "/tmp/frozen_inventory_decision_matrix",
    "/tmp/frozen_inventory_archive_plan",
]

# Retention classes
RETENTION_CLASSES = [
    "KEEP_LATEST",
    "KEEP_TAGGED",
    "KEEP_FOR_AUDIT",
    "TEMP_REGENERABLE",
    "REVIEW_REQUIRED",
    "UNKNOWN",
]

# File types to recognize
ARTIFACT_TYPES = {
    ".json": "json",
    ".md": "markdown",
    ".html": "html",
    ".txt": "text",
    ".csv": "csv",
    ".log": "log",
}


@dataclass
class ArtifactRecord:
    path: str
    artifact_type: str
    size_bytes: int
    sha256: str
    json_valid: bool
    has_markdown: bool
    has_html: bool
    source_phase: str
    safety_flags: dict[str, Any] = field(default_factory=dict)
    release_hold: str = "HOLD"
    advisory_only: bool = True
    retention_class: str = "UNKNOWN"
    review_priority: str = "medium"


@dataclass
class CatalogResult:
    artifacts: list[ArtifactRecord]
    manifest: dict[str, Any]
    scanned_dirs: list[str]
    missing_dirs: list[str]


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _check_json_valid(path: pathlib.Path) -> bool:
    try:
        json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return True
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False


def _detect_artifact_type(path: pathlib.Path) -> str:
    suffix = path.suffix.lower()
    return ARTIFACT_TYPES.get(suffix, "unknown")


def _detect_source_phase(dir_name: str) -> str:
    phase_map = {
        "multi_strategy_research_workbench": "workbench",
        "multi_strategy_research_quality_gate": "quality_gate",
        "research_artifact_browser": "artifact_browser",
        "research_comparison_analytics": "comparison_analytics",
        "research_human_review_packet": "human_review",
        "offline_research_operator_bundle": "operator_bundle",
        "offline_research_experiment_library_validation": "experiment_library",
        "offline_research_governance_validation": "governance",
        "frozen_inventory_review": "frozen_inventory",
        "frozen_inventory_decision_matrix": "decision_matrix",
        "frozen_inventory_archive_plan": "archive_plan",
    }
    for key, phase in phase_map.items():
        if key in dir_name:
            return phase
    return "unknown"


def _extract_safety_flags(path: pathlib.Path) -> dict[str, Any]:
    """Try to read safety flags from a manifest file if present."""
    # Check if this is a manifest file
    if "manifest" in path.name.lower() and path.suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            flags = {}
            for key in ("release_hold", "advisory_only", "human_review_required",
                        "no_live", "no_submit", "no_network", "no_execution", "no_import"):
                if key in data:
                    flags[key] = data[key]
            return flags
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return {}


def _determine_retention(artifact_type: str, source_phase: str, has_manifest: bool) -> str:
    if artifact_type == "json" and "manifest" in source_phase:
        return "KEEP_FOR_AUDIT"
    if source_phase in ("frozen_inventory", "decision_matrix", "archive_plan"):
        return "KEEP_FOR_AUDIT"
    if source_phase in ("quality_gate", "governance"):
        return "KEEP_TAGGED"
    if artifact_type in ("json", "markdown"):
        return "KEEP_LATEST"
    if artifact_type in ("log", "text"):
        return "TEMP_REGENERABLE"
    return "REVIEW_REQUIRED"


def _determine_priority(source_phase: str, has_safety_flags: bool) -> str:
    if source_phase in ("frozen_inventory", "decision_matrix", "archive_plan"):
        return "high"
    if source_phase in ("governance", "quality_gate"):
        return "high"
    if has_safety_flags:
        return "high"
    if source_phase in ("human_review", "operator_bundle"):
        return "medium"
    return "low"


def scan_artifacts(
    scan_dirs: list[str] | None = None,
    *,
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> CatalogResult:
    """Scan offline output directories for research artifacts."""
    dirs = scan_dirs or DEFAULT_SCAN_DIRS
    artifacts: list[ArtifactRecord] = []
    scanned: list[str] = []
    missing: list[str] = []

    for dir_path_str in dirs:
        dir_path = pathlib.Path(dir_path_str)
        if not dir_path.is_dir():
            missing.append(dir_path_str)
            continue
        scanned.append(dir_path_str)

        source_phase = _detect_source_phase(dir_path_str)

        # Walk directory
        for file_path in sorted(dir_path.rglob("*")):
            if not file_path.is_file():
                continue

            artifact_type = _detect_artifact_type(file_path)
            size = file_path.stat().st_size
            sha = _sha256_file(file_path)
            json_valid = _check_json_valid(file_path) if artifact_type == "json" else False
            has_md = any(
                (dir_path / f).suffix.lower() == ".md"
                for f in os.listdir(dir_path)
                if (dir_path / f).is_file()
            ) if dir_path.is_dir() else False
            has_html = any(
                (dir_path / f).suffix.lower() == ".html"
                for f in os.listdir(dir_path)
                if (dir_path / f).is_file()
            ) if dir_path.is_dir() else False
            safety_flags = _extract_safety_flags(file_path)
            rel_path = str(file_path)

            retention = _determine_retention(artifact_type, source_phase, bool(safety_flags))
            priority = _determine_priority(source_phase, bool(safety_flags))

            record = ArtifactRecord(
                path=rel_path,
                artifact_type=artifact_type,
                size_bytes=size,
                sha256=sha,
                json_valid=json_valid,
                has_markdown=has_md,
                has_html=has_html,
                source_phase=source_phase,
                safety_flags=safety_flags,
                release_hold=release_hold,
                advisory_only=True,
                retention_class=retention,
                review_priority=priority,
            )
            artifacts.append(record)

    manifest = _build_manifest(artifacts, scanned, missing, release_hold)
    return CatalogResult(
        artifacts=artifacts,
        manifest=manifest,
        scanned_dirs=scanned,
        missing_dirs=missing,
    )


def _build_manifest(
    artifacts: list[ArtifactRecord],
    scanned: list[str],
    missing: list[str],
    release_hold: str,
) -> dict[str, Any]:
    type_counts: dict[str, int] = {}
    retention_counts: dict[str, int] = {}
    phase_counts: dict[str, int] = {}

    for a in artifacts:
        type_counts[a.artifact_type] = type_counts.get(a.artifact_type, 0) + 1
        retention_counts[a.retention_class] = retention_counts.get(a.retention_class, 0) + 1
        phase_counts[a.source_phase] = phase_counts.get(a.source_phase, 0) + 1

    return {
        "release_hold": release_hold,
        "advisory_only": True,
        "human_review_required": True,
        "no_live": True,
        "no_submit": True,
        "no_exchange": True,
        "no_network": True,
        "no_execution": True,
        "no_import": True,
        "generated_by": "offline_research_result_catalog.py",
        "total_artifacts": len(artifacts),
        "scanned_dirs": scanned,
        "missing_dirs": missing,
        "type_counts": type_counts,
        "retention_counts": retention_counts,
        "phase_counts": phase_counts,
    }


def validate_release_hold(release_hold: str) -> bool:
    return release_hold == RELEASE_HOLD_REQUIRED


def write_json(catalog: CatalogResult, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "manifest": catalog.manifest,
        "scanned_dirs": catalog.scanned_dirs,
        "missing_dirs": catalog.missing_dirs,
        "artifacts": [_record_to_dict(a) for a in catalog.artifacts],
    }
    out_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_manifest(catalog: CatalogResult, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(catalog.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(catalog: CatalogResult, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Offline Research Result Catalog")
    lines.append("")
    lines.append(f"**release_hold:** {catalog.manifest['release_hold']}")
    lines.append(f"**advisory_only:** {catalog.manifest['advisory_only']}")
    lines.append(f"**total artifacts:** {len(catalog.artifacts)}")
    lines.append("")

    lines.append("## Scanned Directories")
    lines.append("")
    for d in catalog.scanned_dirs:
        lines.append(f"- {d}")
    if catalog.missing_dirs:
        lines.append("")
        lines.append("## Missing Directories (skipped)")
        lines.append("")
        for d in catalog.missing_dirs:
            lines.append(f"- {d}")
    lines.append("")

    lines.append("## Retention Summary")
    lines.append("")
    for cls, count in sorted(catalog.manifest["retention_counts"].items()):
        lines.append(f"- {cls}: {count}")
    lines.append("")

    lines.append("## Artifacts")
    lines.append("")
    lines.append("| Path | Type | Size | Retention | Priority | JSON Valid |")
    lines.append("|------|------|------|-----------|----------|------------|")
    for a in catalog.artifacts:
        jv = "Yes" if a.json_valid else "No"
        lines.append(f"| {a.path} | {a.artifact_type} | {a.size_bytes} | {a.retention_class} | {a.review_priority} | {jv} |")
    lines.append("")

    lines.append("## Safety Boundary")
    lines.append("")
    lines.append("- No network imports")
    lines.append("- No scanning repo frozen files")
    lines.append("- release_hold = HOLD")
    lines.append("- Advisory only. Human review required.")
    lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _record_to_dict(rec: ArtifactRecord) -> dict[str, Any]:
    return {
        "path": rec.path,
        "artifact_type": rec.artifact_type,
        "size_bytes": rec.size_bytes,
        "sha256": rec.sha256,
        "json_valid": rec.json_valid,
        "has_markdown": rec.has_markdown,
        "has_html": rec.has_html,
        "source_phase": rec.source_phase,
        "safety_flags": rec.safety_flags,
        "release_hold": rec.release_hold,
        "advisory_only": rec.advisory_only,
        "retention_class": rec.retention_class,
        "review_priority": rec.review_priority,
    }
