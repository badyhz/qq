"""Offline shadow bundle builder -- pure functions, no I/O.

Assembles artifact descriptors for the research bundle.  File I/O is
handled by the CLI script, not this module.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


# ---------------------------------------------------------------------------
# manifest builder
# ---------------------------------------------------------------------------

def build_manifest(artifacts: list[dict[str, str]]) -> dict[str, Any]:
    """Build the bundle manifest.

    Parameters
    ----------
    artifacts : list[dict]
        Each dict has ``name`` (str) and ``sha256`` (str).

    Returns
    -------
    dict
        Manifest with safety flags and artifact inventory.
    """
    return {
        "release_hold": "HOLD",
        "no_live": True,
        "no_submit": True,
        "no_exchange": True,
        "artifact_count": len(artifacts),
        "artifacts": list(artifacts),
    }


# ---------------------------------------------------------------------------
# content hash
# ---------------------------------------------------------------------------

def compute_sha256(content: str | bytes) -> str:
    """Compute SHA-256 hex digest of content.

    Parameters
    ----------
    content : str or bytes
        Content to hash.

    Returns
    -------
    str
        Hex-encoded SHA-256 digest.
    """
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


# ---------------------------------------------------------------------------
# bundle assembly (pure -- returns dict of name -> content)
# ---------------------------------------------------------------------------

def build_bundle(
    plan_data: dict[str, Any],
    matrix_data: dict[str, Any],
    results_data: list[dict[str, Any]],
    scorecard_data: dict[str, Any],
    report_markdown: str,
    report_html: str,
    report_json: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the full bundle as a dict of artifact contents.

    Parameters
    ----------
    plan_data : dict
        Experiment plan as JSON-serializable dict.
    matrix_data : dict
        Materialized matrix as JSON-serializable dict.
    results_data : list[dict]
        Evaluation results.
    scorecard_data : dict
        Scorecard data.
    report_markdown : str
        Markdown report content.
    report_html : str
        HTML report content.
    report_json : dict
        JSON report content.

    Returns
    -------
    dict
        Keys are artifact filenames, values are their string content.
        Also includes a ``manifest`` key with the bundle manifest.
    """
    artifacts_content: dict[str, str] = {
        "plan.json": json.dumps(plan_data, indent=2, sort_keys=True),
        "matrix.json": json.dumps(matrix_data, indent=2, sort_keys=True),
        "results.json": json.dumps(results_data, indent=2, sort_keys=True),
        "scorecard.json": json.dumps(scorecard_data, indent=2, sort_keys=True),
        "report.md": report_markdown,
        "report.html": report_html,
        "report.json": json.dumps(report_json, indent=2, sort_keys=True),
    }

    artifact_descriptors: list[dict[str, str]] = []
    for name, content in sorted(artifacts_content.items()):
        artifact_descriptors.append({
            "name": name,
            "sha256": compute_sha256(content),
        })

    manifest = build_manifest(artifact_descriptors)

    result: dict[str, Any] = dict(artifacts_content)
    result["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True)
    return result
