"""Research artifact compare — compare two browser outputs.

Program F: Bundle comparison UX. Offline only. No network.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class ArtifactDiff:
    """Diff entry for a single artifact."""
    name: str
    change_type: str  # added / removed / changed / unchanged
    left_sha256: str
    right_sha256: str


@dataclass(frozen=True)
class BrowserComparisonResult:
    """Complete comparison result."""
    status: str  # PASS / PARTIAL / FAIL
    identical_safety_flags: bool
    identical_verdict: bool
    identical_composite_score: bool
    verdict_diff: Dict[str, str]
    composite_score_diff: Dict[str, float]
    blocker_diff: Dict[str, List[str]]
    warning_diff: Dict[str, List[str]]
    safety_flag_diff: Dict[str, Dict[str, Any]]
    artifact_diffs: Tuple[ArtifactDiff, ...]
    added_artifacts: Tuple[str, ...]
    removed_artifacts: Tuple[str, ...]
    changed_artifacts: Tuple[str, ...]
    unchanged_artifacts: Tuple[str, ...]


def compare_browser_outputs(
    left_dir: Path,
    right_dir: Path,
    require_identical_safety_flags: bool = True,
) -> BrowserComparisonResult:
    """Compare two artifact browser output directories."""
    left_index = _load_json(left_dir, "artifact_browser_index.json")
    right_index = _load_json(right_dir, "artifact_browser_index.json")

    left_entries = {e["name"]: e for e in left_index.get("entries", [])}
    right_entries = {e["name"]: e for e in right_index.get("entries", [])}

    all_names = sorted(set(list(left_entries.keys()) + list(right_entries.keys())))

    artifact_diffs: List[ArtifactDiff] = []
    added: List[str] = []
    removed: List[str] = []
    changed: List[str] = []
    unchanged: List[str] = []

    for name in all_names:
        le = left_entries.get(name)
        re = right_entries.get(name)

        if le is None and re is not None:
            artifact_diffs.append(ArtifactDiff(
                name=name, change_type="added",
                left_sha256="", right_sha256=re.get("sha256", ""),
            ))
            added.append(name)
        elif le is not None and re is None:
            artifact_diffs.append(ArtifactDiff(
                name=name, change_type="removed",
                left_sha256=le.get("sha256", ""), right_sha256="",
            ))
            removed.append(name)
        else:
            l_sha = le.get("sha256", "")
            r_sha = re.get("sha256", "")
            if l_sha != r_sha:
                artifact_diffs.append(ArtifactDiff(
                    name=name, change_type="changed",
                    left_sha256=l_sha, right_sha256=r_sha,
                ))
                changed.append(name)
            else:
                artifact_diffs.append(ArtifactDiff(
                    name=name, change_type="unchanged",
                    left_sha256=l_sha, right_sha256=r_sha,
                ))
                unchanged.append(name)

    # --- Compare review models ---
    left_model = _load_json(left_dir, "review_model.json")
    right_model = _load_json(right_dir, "review_model.json")

    verdict_diff: Dict[str, str] = {}
    if left_model.get("verdict") != right_model.get("verdict"):
        verdict_diff = {
            "left": left_model.get("verdict", ""),
            "right": right_model.get("verdict", ""),
        }

    score_diff: Dict[str, float] = {}
    if left_model.get("composite_score") != right_model.get("composite_score"):
        score_diff = {
            "left": left_model.get("composite_score", 0),
            "right": right_model.get("composite_score", 0),
        }

    # --- Blocker / warning diff ---
    left_blocks = set(left_model.get("blockers", []))
    right_blocks = set(right_model.get("blockers", []))
    blocker_diff: Dict[str, List[str]] = {}
    if left_blocks != right_blocks:
        blocker_diff = {
            "added": sorted(right_blocks - left_blocks),
            "removed": sorted(left_blocks - right_blocks),
        }

    left_warns = set(left_model.get("warnings", []))
    right_warns = set(right_model.get("warnings", []))
    warning_diff: Dict[str, List[str]] = {}
    if left_warns != right_warns:
        warning_diff = {
            "added": sorted(right_warns - left_warns),
            "removed": sorted(left_warns - right_warns),
        }

    # --- Safety flag diff ---
    left_sf = left_model.get("safety_flags", {})
    right_sf = right_model.get("safety_flags", {})
    sf_diff: Dict[str, Dict[str, Any]] = {}
    all_sf_keys = sorted(set(list(left_sf.keys()) + list(right_sf.keys())))
    for k in all_sf_keys:
        lv = left_sf.get(k)
        rv = right_sf.get(k)
        if lv != rv:
            sf_diff[k] = {"left": lv, "right": rv}

    # --- Status determination ---
    identical_safety = len(sf_diff) == 0
    identical_verdict = len(verdict_diff) == 0
    identical_score = len(score_diff) == 0

    if require_identical_safety_flags and not identical_safety:
        status = "FAIL"
    elif identical_verdict and identical_score and not changed and not added and not removed:
        status = "PASS"
    elif identical_safety:
        status = "PARTIAL"
    else:
        status = "FAIL"

    return BrowserComparisonResult(
        status=status,
        identical_safety_flags=identical_safety,
        identical_verdict=identical_verdict,
        identical_composite_score=identical_score,
        verdict_diff=verdict_diff,
        composite_score_diff=score_diff,
        blocker_diff=blocker_diff,
        warning_diff=warning_diff,
        safety_flag_diff=sf_diff,
        artifact_diffs=tuple(artifact_diffs),
        added_artifacts=tuple(sorted(added)),
        removed_artifacts=tuple(sorted(removed)),
        changed_artifacts=tuple(sorted(changed)),
        unchanged_artifacts=tuple(sorted(unchanged)),
    )


def comparison_to_dict(r: BrowserComparisonResult) -> Dict[str, Any]:
    """Serialize comparison result to dict."""
    return {
        "status": r.status,
        "identical_safety_flags": r.identical_safety_flags,
        "identical_verdict": r.identical_verdict,
        "identical_composite_score": r.identical_composite_score,
        "verdict_diff": r.verdict_diff,
        "composite_score_diff": r.composite_score_diff,
        "blocker_diff": r.blocker_diff,
        "warning_diff": r.warning_diff,
        "safety_flag_diff": r.safety_flag_diff,
        "artifact_diffs": [
            {"name": d.name, "change_type": d.change_type,
             "left_sha256": d.left_sha256, "right_sha256": d.right_sha256}
            for d in r.artifact_diffs
        ],
        "added_artifacts": list(r.added_artifacts),
        "removed_artifacts": list(r.removed_artifacts),
        "changed_artifacts": list(r.changed_artifacts),
        "unchanged_artifacts": list(r.unchanged_artifacts),
    }


def comparison_to_json(r: BrowserComparisonResult) -> str:
    """Serialize comparison to JSON."""
    return json.dumps(comparison_to_dict(r), sort_keys=True, indent=2)


def comparison_to_markdown(r: BrowserComparisonResult) -> str:
    """Render comparison result as markdown."""
    lines = [
        "# Artifact Browser Comparison",
        "",
        f"Status: **{r.status}**",
        "",
        "## Safety Flags",
        "",
        f"- Identical safety flags: {r.identical_safety_flags}",
        "",
    ]

    if r.safety_flag_diff:
        lines.append("### Safety Flag Differences")
        lines.append("")
        for k, v in sorted(r.safety_flag_diff.items()):
            lines.append(f"- {k}: left={v['left']}, right={v['right']}")
        lines.append("")

    # Verdict / score
    lines.extend(["## Verdict / Score", ""])
    lines.append(f"- Identical verdict: {r.identical_verdict}")
    lines.append(f"- Identical composite score: {r.identical_composite_score}")
    if r.verdict_diff:
        lines.append(f"- Verdict: left={r.verdict_diff.get('left')}, right={r.verdict_diff.get('right')}")
    if r.composite_score_diff:
        lines.append(f"- Score: left={r.composite_score_diff.get('left')}, right={r.composite_score_diff.get('right')}")
    lines.append("")

    # Blockers / warnings
    if r.blocker_diff:
        lines.extend(["## Blocker Differences", ""])
        for k, items in sorted(r.blocker_diff.items()):
            for item in items:
                lines.append(f"- {k}: {item}")
        lines.append("")

    if r.warning_diff:
        lines.extend(["## Warning Differences", ""])
        for k, items in sorted(r.warning_diff.items()):
            for item in items:
                lines.append(f"- {k}: {item}")
        lines.append("")

    # Artifact diffs
    lines.extend(["## Artifact Differences", ""])
    if r.added_artifacts:
        lines.append("### Added")
        for a in r.added_artifacts:
            lines.append(f"- {a}")
        lines.append("")
    if r.removed_artifacts:
        lines.append("### Removed")
        for a in r.removed_artifacts:
            lines.append(f"- {a}")
        lines.append("")
    if r.changed_artifacts:
        lines.append("### Changed")
        for a in r.changed_artifacts:
            lines.append(f"- {a}")
        lines.append("")
    if r.unchanged_artifacts:
        lines.append(f"### Unchanged: {len(r.unchanged_artifacts)} artifacts")
        lines.append("")

    lines.extend([
        "---",
        "",
        "**Advisory only. No auto-promotion. release_hold remains HOLD.**",
        "",
    ])

    return "\n".join(lines)


def _load_json(directory: Path, name: str) -> Dict[str, Any]:
    """Load JSON file, return empty dict on failure."""
    p = directory / name
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError):
        return {}
