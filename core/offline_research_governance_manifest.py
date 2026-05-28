"""Offline research governance manifest — emit governance validation artifacts.

No network. No exchange. No runtime. No planner. Advisory only.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from core.offline_research_governance import run_full_governance_validation


def emit_governance_validation(
    docs_root: Path,
    output_dir: Path,
    release_hold: str = "HOLD",
) -> Dict[str, Any]:
    """Run governance validation and emit JSON + MD reports."""
    output_dir.mkdir(parents=True, exist_ok=True)

    result = run_full_governance_validation(docs_root, release_hold)

    # JSON validation result
    validation_json = output_dir / "governance_validation.json"
    with open(validation_json, "w") as f:
        json.dump(result, f, indent=2, sort_keys=True)

    # Markdown report
    validation_md = output_dir / "governance_validation.md"
    md_lines = [
        "# Offline Research Governance Validation",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"**release_hold:** {result['release_hold']}",
        f"**Valid:** {'PASS' if result['valid'] else 'FAIL'}",
        "",
        "## Errors",
        "",
    ]
    if result["errors"]:
        for err in result["errors"]:
            md_lines.append(f"- {err}")
    else:
        md_lines.append("- None")
    md_lines.extend(["", "## Summary", ""])
    md_lines.append(f"- Doc check: {'PASS' if result['doc_check']['valid'] else 'FAIL'} ({result['doc_check']['found']}/{result['doc_check']['total_required']})")
    md_lines.append(f"- Safety check: {'PASS' if result['safety_check'] else 'FAIL'}")
    md_lines.append(f"- Approval check: {'PASS' if result['approval_check'] else 'FAIL'}")
    md_lines.append(f"- Untracked warning: {'PASS' if result['untracked_warning_check'] else 'FAIL'}")
    validation_md.write_text("\n".join(md_lines))

    # Manifest
    manifest = {
        "version": "1.0.0",
        "generated_by": "offline_research_governance_manifest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_hold": release_hold,
        "advisory_only": True,
        "human_review_required": True,
        "validation_result": result["valid"],
        "error_count": len(result["errors"]),
        "artifacts": [
            str(validation_json),
            str(validation_md),
        ],
    }
    manifest_json = output_dir / "governance_manifest.json"
    with open(manifest_json, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    return {
        "validation_json": str(validation_json),
        "validation_md": str(validation_md),
        "manifest_json": str(manifest_json),
        "valid": result["valid"],
        "errors": result["errors"],
    }
