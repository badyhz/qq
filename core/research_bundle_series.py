"""Research bundle series — load and normalize multiple bundles for comparison.

Program A: Bundle Series Loader.
Load 2+ quality gate bundles or artifact browser bundles.
Produce normalized bundle records with deterministic ordering.

No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Required files for quality gate bundles
QUALITY_GATE_REQUIRED: Tuple[str, ...] = (
    "manifest.json",
    "quality_gate_summary.json",
)

# Required files for artifact browser bundles
ARTIFACT_BROWSER_REQUIRED: Tuple[str, ...] = (
    "artifact_browser_manifest.json",
    "review_model.json",
)

MANIFEST_SAFETY_KEYS: Dict[str, object] = {
    "release_hold": "HOLD",
    "no_live": True,
    "no_submit": True,
    "no_exchange": True,
    "no_runtime_integration": True,
    "no_planner_integration": True,
    "no_network": True,
    "advisory_only": True,
    "human_review_required": True,
}


@dataclass(frozen=True)
class BundleRecord:
    """Normalized bundle record."""
    label: str
    path: str
    manifest: Dict[str, Any]
    quality_summary: Dict[str, Any]
    artifact_hashes: Dict[str, str]
    safety_valid: bool
    safety_errors: Tuple[str, ...]
    json_parse_ok: bool
    parse_errors: Tuple[str, ...]


def load_bundle_series(
    bundles: List[Tuple[str, Path]],
    strict: bool = True,
    release_hold: str = "HOLD",
) -> Tuple[BundleRecord, ...]:
    """Load and validate a series of labeled bundles.

    Args:
        bundles: List of (label, path) tuples. Must be >= 2.
        strict: If True, enforce all safety checks.
        release_hold: Expected release_hold value.

    Returns:
        Tuple of BundleRecord, sorted by label for deterministic ordering.

    Raises:
        ValueError: If fewer than 2 bundles, missing files, or safety violations.
    """
    if len(bundles) < 2:
        raise ValueError(f"Need at least 2 bundles, got {len(bundles)}")

    records: List[BundleRecord] = []
    errors: List[str] = []

    for label, path in bundles:
        record_errors: List[str] = []

        if not path.exists():
            record_errors.append(f"Bundle directory missing: {path}")
            records.append(BundleRecord(
                label=label, path=str(path),
                manifest={}, quality_summary={},
                artifact_hashes={}, safety_valid=False,
                safety_errors=tuple(record_errors), json_parse_ok=False,
                parse_errors=tuple(record_errors),
            ))
            continue

        # Detect bundle format: quality gate or artifact browser
        is_quality_gate = (path / "manifest.json").exists()
        is_artifact_browser = (path / "artifact_browser_manifest.json").exists()

        if is_quality_gate:
            # Quality gate format
            manifest, m_ok, m_err = _load_json_safe(path / "manifest.json")
            if not m_ok:
                record_errors.extend(m_err)

            qgs, q_ok, q_err = _load_json_safe(path / "quality_gate_summary.json")
            if not q_ok:
                record_errors.extend(q_err)

            for req in QUALITY_GATE_REQUIRED:
                if not (path / req).exists():
                    record_errors.append(f"Missing required file: {req}")

        elif is_artifact_browser:
            # Artifact browser format
            manifest, m_ok, m_err = _load_json_safe(path / "artifact_browser_manifest.json")
            if not m_ok:
                record_errors.extend(m_err)

            qgs, q_ok, q_err = _load_json_safe(path / "review_model.json")
            if not q_ok:
                record_errors.extend(q_err)

            for req in ARTIFACT_BROWSER_REQUIRED:
                if not (path / req).exists():
                    record_errors.append(f"Missing required file: {req}")

        else:
            # Neither format found
            record_errors.append("No manifest.json or artifact_browser_manifest.json found")
            manifest, m_ok, qgs, q_ok = {}, False, {}, False

        # Safety validation
        safety_errors: List[str] = []
        if m_ok:
            if is_artifact_browser:
                # Browser manifest has different safety structure
                # Check release_hold from manifest
                rh = manifest.get("release_hold", "UNKNOWN")
                if rh != release_hold:
                    safety_errors.append(
                        f"manifest.release_hold={rh!r}, expected {release_hold!r}"
                    )
                # Check safety flags from review_model
                if q_ok:
                    sf = qgs.get("safety_flags", {})
                    for key in ("advisory_only", "human_review_required", "no_live",
                                "no_submit", "no_exchange", "no_network"):
                        val = sf.get(key)
                        if val is not True:
                            safety_errors.append(
                                f"safety_flags.{key}={val!r}, expected True"
                            )
                    if not sf.get("release_hold_is_HOLD", False):
                        safety_errors.append("safety_flags.release_hold_is_HOLD=False, expected True")
            else:
                for key, expected in MANIFEST_SAFETY_KEYS.items():
                    actual = manifest.get(key)
                    if actual != expected:
                        safety_errors.append(
                            f"manifest.{key}={actual!r}, expected {expected!r}"
                        )
                if manifest.get("release_hold") != release_hold:
                    safety_errors.append(
                        f"manifest.release_hold={manifest.get('release_hold')!r}, "
                        f"expected {release_hold!r}"
                    )

        # Compute artifact hashes
        artifact_hashes: Dict[str, str] = {}
        if path.exists():
            for f in sorted(path.iterdir()):
                if f.is_file() and f.suffix == ".json":
                    try:
                        raw = f.read_bytes()
                        artifact_hashes[f.name] = hashlib.sha256(raw).hexdigest()
                    except OSError:
                        pass

        safety_valid = len(safety_errors) == 0

        records.append(BundleRecord(
            label=label,
            path=str(path),
            manifest=manifest,
            quality_summary=qgs,
            artifact_hashes=artifact_hashes,
            safety_valid=safety_valid,
            safety_errors=tuple(sorted(safety_errors)),
            json_parse_ok=m_ok and q_ok,
            parse_errors=tuple(sorted(record_errors)),
        ))

    # Strict mode: fail on any errors
    if strict:
        all_errors = []
        for r in records:
            if not r.json_parse_ok:
                all_errors.append(f"[{r.label}] parse errors: {r.parse_errors}")
            if not r.safety_valid:
                all_errors.append(f"[{r.label}] safety errors: {r.safety_errors}")
        if all_errors:
            raise ValueError(f"Bundle validation failed:\n" + "\n".join(all_errors))

    # Sort by label for deterministic ordering
    return tuple(sorted(records, key=lambda r: r.label))


def bundle_record_to_dict(r: BundleRecord) -> Dict[str, Any]:
    """Serialize bundle record to dict."""
    return {
        "label": r.label,
        "path": r.path,
        "manifest": r.manifest,
        "quality_summary": r.quality_summary,
        "artifact_hashes": r.artifact_hashes,
        "safety_valid": r.safety_valid,
        "safety_errors": list(r.safety_errors),
        "json_parse_ok": r.json_parse_ok,
        "parse_errors": list(r.parse_errors),
    }


def build_bundle_series_index(
    records: Tuple[BundleRecord, ...],
    generated_at: str = "deterministic",
) -> Dict[str, Any]:
    """Build bundle_series_index.json content."""
    return {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "bundle_count": len(records),
        "bundles": [bundle_record_to_dict(r) for r in records],
        "all_safety_valid": all(r.safety_valid for r in records),
        "all_json_parse_ok": all(r.json_parse_ok for r in records),
    }


def _load_json_safe(path: Path) -> Tuple[Dict[str, Any], bool, List[str]]:
    """Load JSON file safely. Returns (data, ok, errors)."""
    if not path.exists():
        return {}, False, [f"File missing: {path.name}"]
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            return {}, False, [f"{path.name}: not a JSON object"]
        return data, True, []
    except (json.JSONDecodeError, ValueError) as e:
        return {}, False, [f"{path.name}: corrupted JSON: {e}"]
