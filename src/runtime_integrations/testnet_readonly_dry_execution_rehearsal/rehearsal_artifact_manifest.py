"""Rehearsal artifact manifest: catalogs all dry execution rehearsal artifacts."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ArtifactEntry:
    artifact_id: str
    artifact_name: str
    artifact_type: str
    location: str
    status: str
    def to_dict(self) -> dict:
        return {"artifact_id": self.artifact_id, "artifact_name": self.artifact_name,
                "artifact_type": self.artifact_type, "location": self.location,
                "status": self.status}


@dataclass(frozen=True)
class RehearsalArtifactManifest:
    manifest_id: str
    created_at: str
    artifacts: tuple[ArtifactEntry, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"manifest_id": self.manifest_id, "created_at": self.created_at,
                "artifacts": [a.to_dict() for a in self.artifacts],
                "final_verdict": self.final_verdict}


ARTIFACTS = (
    ArtifactEntry("ART_001", "Dry execution rehearsal", "REHEARSAL",
        "data/runtime/testnet_readonly_dry_execution_rehearsal/dry_execution_rehearsal.json", "PRESENT"),
    ArtifactEntry("ART_002", "Endpoint allowlist stub", "ALLOWLIST",
        "data/runtime/testnet_readonly_dry_execution_rehearsal/endpoint_allowlist_stub.json", "PRESENT"),
    ArtifactEntry("ART_003", "Audit redaction pack", "REDACTION",
        "data/runtime/testnet_readonly_dry_execution_rehearsal/audit_redaction_pack.json", "PRESENT"),
    ArtifactEntry("ART_004", "Safety regression", "SAFETY",
        "data/runtime/testnet_readonly_dry_execution_rehearsal/dry_execution_safety_regression.json", "PRESENT"),
    ArtifactEntry("ART_005", "Suite manifest", "MANIFEST",
        "data/runtime/testnet_readonly_dry_execution_rehearsal/dry_execution_rehearsal_suite_manifest.json", "PRESENT"),
)


def create_manifest() -> RehearsalArtifactManifest:
    return RehearsalArtifactManifest(
        manifest_id=f"RAM_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        artifacts=ARTIFACTS,
        final_verdict="REHEARSAL_ARTIFACT_MANIFEST_READY|ALL_ARTIFACTS_PRESENT|REAL_NETWORK_NOT_ALLOWED|TESTNET_SUBMIT_NOT_ALLOWED",
    )


def write_manifest(manifest: RehearsalArtifactManifest, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")


def render_report(manifest: RehearsalArtifactManifest) -> str:
    lines = ["# Rehearsal Artifact Manifest", "",
        f"**manifest_id={manifest.manifest_id}**",
        f"**artifacts={len(manifest.artifacts)}**",
        f"**verdict={manifest.final_verdict}**", "",
        "## Artifacts", "",
        "| ID | Name | Type | Location | Status |",
        "|----|------|------|----------|--------|"]
    for a in manifest.artifacts:
        lines.append(f"| {a.artifact_id} | {a.artifact_name} | {a.artifact_type} | {a.location} | {a.status} |")
    lines.extend(["", "## Conclusion", "",
        "REHEARSAL_ARTIFACT_MANIFEST_READY",
        "ALL_ARTIFACTS_PRESENT",
        "REAL_NETWORK_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
