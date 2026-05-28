"""Research artifact browser — index, validate, build review model.

Programs A, B, C combined. Offline only. No network. No exchange.
No runtime. No planner. No auto-promotion.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.research_artifact_schema import (
    ARTIFACT_SCHEMA_KEYS,
    BROWSER_OPTIONAL_ARTIFACTS,
    BROWSER_REQUIRED_ARTIFACTS,
    MANIFEST_SAFETY_CHECKS,
)


# === Program A: Artifact Indexer ===


@dataclass(frozen=True)
class ArtifactIndexEntry:
    """Single artifact index entry."""
    name: str
    required: bool
    exists: bool
    sha256: str
    size_bytes: int
    json_parse_ok: bool
    top_level_keys: Tuple[str, ...]


@dataclass(frozen=True)
class ArtifactBrowserIndex:
    """Complete artifact browser index."""
    schema_version: str
    generated_at: str
    release_hold: str
    advisory_only: bool
    entries: Tuple[ArtifactIndexEntry, ...]
    required_present: int
    required_missing: int
    optional_present: int
    status: str  # PASS / FAIL


def build_artifact_browser_index(
    quality_dir: Path,
    generated_at: str = "deterministic",
) -> ArtifactBrowserIndex:
    """Index all quality gate artifacts. Deterministic sorted order."""
    entries: List[ArtifactIndexEntry] = []

    all_artifacts = sorted(set(BROWSER_REQUIRED_ARTIFACTS + BROWSER_OPTIONAL_ARTIFACTS))

    for name in all_artifacts:
        p = quality_dir / name
        required = name in BROWSER_REQUIRED_ARTIFACTS

        if p.exists():
            raw = p.read_bytes()
            sha = hashlib.sha256(raw).hexdigest()
            size = len(raw)
            json_ok = False
            keys: Tuple[str, ...] = ()

            if p.suffix == ".json":
                try:
                    data = json.loads(raw)
                    if isinstance(data, dict):
                        keys = tuple(sorted(data.keys()))
                    json_ok = True
                except (json.JSONDecodeError, ValueError):
                    json_ok = False

            entries.append(ArtifactIndexEntry(
                name=name, required=required, exists=True,
                sha256=sha, size_bytes=size,
                json_parse_ok=json_ok, top_level_keys=keys,
            ))
        else:
            entries.append(ArtifactIndexEntry(
                name=name, required=required, exists=False,
                sha256="", size_bytes=0,
                json_parse_ok=False, top_level_keys=(),
            ))

    required_present = sum(1 for e in entries if e.required and e.exists)
    required_missing = sum(1 for e in entries if e.required and not e.exists)
    optional_present = sum(1 for e in entries if not e.required and e.exists)

    status = "PASS" if required_missing == 0 else "FAIL"

    return ArtifactBrowserIndex(
        schema_version="1.0.0",
        generated_at=generated_at,
        release_hold="HOLD",
        advisory_only=True,
        entries=tuple(entries),
        required_present=required_present,
        required_missing=required_missing,
        optional_present=optional_present,
        status=status,
    )


def artifact_browser_index_to_dict(idx: ArtifactBrowserIndex) -> Dict[str, Any]:
    """Serialize browser index to dict."""
    return {
        "schema_version": idx.schema_version,
        "generated_at": idx.generated_at,
        "release_hold": idx.release_hold,
        "advisory_only": idx.advisory_only,
        "entries": [
            {
                "name": e.name,
                "required": e.required,
                "exists": e.exists,
                "sha256": e.sha256,
                "size_bytes": e.size_bytes,
                "json_parse_ok": e.json_parse_ok,
                "top_level_keys": list(e.top_level_keys),
            }
            for e in idx.entries
        ],
        "required_present": idx.required_present,
        "required_missing": idx.required_missing,
        "optional_present": idx.optional_present,
        "status": idx.status,
    }


# === Program B: Schema Shape Validator ===


@dataclass(frozen=True)
class SchemaValidationResult:
    """Schema validation result."""
    status: str  # PASS / FAIL
    manifest_valid: bool
    safety_flags_valid: bool
    safety_flag_errors: Tuple[str, ...]
    schema_shape_errors: Tuple[str, ...]
    promotion_gate_advisory: bool
    reproducibility_has_hashes: bool
    report_quality_has_sections: bool
    errors: Tuple[str, ...]


def validate_artifact_schema(
    quality_dir: Path,
    expected_release_hold: str = "HOLD",
) -> SchemaValidationResult:
    """Validate artifact schema shapes and safety flags."""
    errors: List[str] = []
    safety_errors: List[str] = []

    # --- Manifest validation ---
    manifest_path = quality_dir / "manifest.json"
    manifest_valid = False
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            manifest_valid = True

            # Check safety flags
            for key, expected_val in MANIFEST_SAFETY_CHECKS.items():
                actual = manifest.get(key)
                if actual != expected_val:
                    safety_errors.append(
                        f"manifest.{key}={actual!r}, expected {expected_val!r}"
                    )

            # Check release_hold specifically
            if manifest.get("release_hold") != expected_release_hold:
                safety_errors.append(
                    f"manifest.release_hold={manifest.get('release_hold')!r}, "
                    f"expected {expected_release_hold!r}"
                )

        except (json.JSONDecodeError, ValueError) as e:
            errors.append(f"manifest.json: corrupted JSON: {e}")
    else:
        errors.append("manifest.json: missing required artifact")

    # --- Schema shape checks ---
    for artifact_name, expected_keys in ARTIFACT_SCHEMA_KEYS.items():
        p = quality_dir / artifact_name
        if not p.exists():
            if artifact_name in BROWSER_REQUIRED_ARTIFACTS:
                errors.append(f"{artifact_name}: missing required artifact")
            continue
        try:
            data = json.loads(p.read_text())
            if not isinstance(data, dict):
                errors.append(f"{artifact_name}: not a JSON object")
                continue
            actual_keys = set(data.keys())
            missing_keys = expected_keys - actual_keys
            if missing_keys:
                errors.append(
                    f"{artifact_name}: missing keys: {sorted(missing_keys)}"
                )
        except (json.JSONDecodeError, ValueError) as e:
            errors.append(f"{artifact_name}: corrupted JSON: {e}")

    # --- Promotion gate advisory check ---
    promo_advisory = False
    promo_path = quality_dir / "promotion_gate_v2.json"
    if promo_path.exists():
        try:
            promo = json.loads(promo_path.read_text())
            promo_advisory = promo.get("advisory_only", False) is True
            if not promo_advisory:
                errors.append("promotion_gate_v2.json: advisory_only must be True")
        except (json.JSONDecodeError, ValueError):
            errors.append("promotion_gate_v2.json: corrupted JSON")

    # --- Reproducibility manifest hash check ---
    repro_has_hashes = False
    repro_path = quality_dir / "reproducibility_manifest.json"
    if repro_path.exists():
        try:
            repro = json.loads(repro_path.read_text())
            has_input = "input_artifact_hashes" in repro or "input_hashes" in repro
            has_output = bool(repro.get("output_artifact_hashes") or repro.get("output_hashes"))
            repro_has_hashes = has_input and has_output
            if not repro_has_hashes:
                errors.append("reproducibility_manifest.json: missing input/output hashes")
        except (json.JSONDecodeError, ValueError):
            errors.append("reproducibility_manifest.json: corrupted JSON")

    # --- Report quality check sections ---
    rqc_has_sections = False
    rqc_path = quality_dir / "report_quality_check.json"
    if rqc_path.exists():
        try:
            rqc = json.loads(rqc_path.read_text())
            sections_present = rqc.get("sections_present") or rqc.get("completeness", {})
            if isinstance(sections_present, list):
                rqc_has_sections = len(sections_present) > 0
            elif isinstance(sections_present, dict):
                rqc_has_sections = bool(sections_present)
            else:
                rqc_has_sections = bool(sections_present)
            if not rqc_has_sections:
                errors.append("report_quality_check.json: no sections_present")
        except (json.JSONDecodeError, ValueError):
            errors.append("report_quality_check.json: corrupted JSON")

    safety_flags_valid = len(safety_errors) == 0
    all_errors = tuple(sorted(safety_errors + errors))
    status = "PASS" if not all_errors else "FAIL"

    return SchemaValidationResult(
        status=status,
        manifest_valid=manifest_valid,
        safety_flags_valid=safety_flags_valid,
        safety_flag_errors=tuple(sorted(safety_errors)),
        schema_shape_errors=tuple(sorted(errors)),
        promotion_gate_advisory=promo_advisory,
        reproducibility_has_hashes=repro_has_hashes,
        report_quality_has_sections=rqc_has_sections,
        errors=all_errors,
    )


def schema_validation_to_dict(r: SchemaValidationResult) -> Dict[str, Any]:
    """Serialize schema validation to dict."""
    return {
        "status": r.status,
        "manifest_valid": r.manifest_valid,
        "safety_flags_valid": r.safety_flags_valid,
        "safety_flag_errors": list(r.safety_flag_errors),
        "schema_shape_errors": list(r.schema_shape_errors),
        "promotion_gate_advisory": r.promotion_gate_advisory,
        "reproducibility_has_hashes": r.reproducibility_has_hashes,
        "report_quality_has_sections": r.report_quality_has_sections,
        "errors": list(r.errors),
    }


# === Program C: Review View Model ===


@dataclass(frozen=True)
class ReviewModel:
    """Normalized review model for human inspection."""
    verdict: str
    composite_score: float
    evidence_completeness: float
    blockers: Tuple[str, ...]
    warnings: Tuple[str, ...]
    safety_flags: Dict[str, bool]
    required_artifact_coverage: float
    strategy_robustness_summary: Dict[str, Any]
    parameter_fragility_summary: Dict[str, Any]
    negative_control_summary: Dict[str, Any]
    bootstrap_confidence_summary: Dict[str, Any]
    regime_warnings: Tuple[str, ...]
    portfolio_overlap_risk: Dict[str, Any]
    reproducibility_status: str


def build_review_model(quality_dir: Path) -> ReviewModel:
    """Build normalized review model from quality gate output."""
    # --- Load quality gate summary ---
    qgs = _load_json(quality_dir, "quality_gate_summary.json")
    verdict = qgs.get("verdict", "UNKNOWN")
    composite_score = qgs.get("composite_score", 0.0)
    evidence_completeness = qgs.get("evidence_completeness", 0.0)
    blockers = tuple(qgs.get("hard_blocks", []))
    warnings = tuple(qgs.get("warnings", []))

    # --- Safety flags from manifest ---
    manifest = _load_json(quality_dir, "manifest.json")
    safety_flags = {
        "release_hold_is_HOLD": manifest.get("release_hold") == "HOLD",
        "no_live": manifest.get("no_live", False),
        "no_submit": manifest.get("no_submit", False),
        "no_exchange": manifest.get("no_exchange", False),
        "no_runtime_integration": manifest.get("no_runtime_integration", False),
        "no_planner_integration": manifest.get("no_planner_integration", False),
        "no_network": manifest.get("no_network", False),
        "advisory_only": manifest.get("advisory_only", False),
        "human_review_required": manifest.get("human_review_required", False),
        "strict_mode": manifest.get("strict_mode", False),
    }

    # --- Artifact coverage ---
    index_data = _load_json(quality_dir, "artifact_index.json")
    total = index_data.get("total_artifacts", 0)
    present = index_data.get("present_count", 0)
    coverage = present / max(total, 1)

    # --- Strategy robustness ---
    strat_rob = _load_json(quality_dir, "strategy_robustness_report.json")
    strat_summary = {
        "verdict": strat_rob.get("verdict", "UNKNOWN"),
        "strategies": strat_rob.get("strategies", {}),
    }

    # --- Parameter fragility ---
    param_frag = _load_json(quality_dir, "parameter_fragility_report.json")
    param_summary = {
        "verdict": param_frag.get("verdict", "UNKNOWN"),
        "strategies": param_frag.get("strategies", {}),
        "hard_blocks": param_frag.get("hard_blocks", []),
    }

    # --- Negative controls ---
    nc = _load_json(quality_dir, "negative_control_report.json")
    nc_summary = {
        "verdict": nc.get("verdict", "UNKNOWN"),
        "baselines": nc.get("baselines", {}),
        "hard_blocks": nc.get("hard_blocks", []),
    }

    # --- Bootstrap ---
    boot = _load_json(quality_dir, "bootstrap_report.json")
    boot_summary = {
        "verdict": boot.get("verdict", "UNKNOWN"),
        "ci_lower": boot.get("ci_lower") or boot.get("worst_case_5pct"),
        "ci_upper": boot.get("ci_upper") or boot.get("bootstrap_mean"),
        "stability": boot.get("stability"),
    }

    # --- Regime ---
    regime = _load_json(quality_dir, "regime_breakdown.json")
    regime_warns = tuple(regime.get("warnings", []))

    # --- Portfolio overlap ---
    overlap = _load_json(quality_dir, "portfolio_overlap_risk.json")
    overlap_summary = {
        "verdict": overlap.get("verdict", "UNKNOWN"),
        "pairs": overlap.get("pairs", []),
        "hard_blocks": overlap.get("hard_blocks", []),
    }

    # --- Reproducibility ---
    repro = _load_json(quality_dir, "reproducibility_manifest.json")
    repro_status = repro.get("verdict", "UNKNOWN")

    return ReviewModel(
        verdict=verdict,
        composite_score=composite_score,
        evidence_completeness=evidence_completeness,
        blockers=blockers,
        warnings=warnings,
        safety_flags=safety_flags,
        required_artifact_coverage=coverage,
        strategy_robustness_summary=strat_summary,
        parameter_fragility_summary=param_summary,
        negative_control_summary=nc_summary,
        bootstrap_confidence_summary=boot_summary,
        regime_warnings=regime_warns,
        portfolio_overlap_risk=overlap_summary,
        reproducibility_status=repro_status,
    )


def review_model_to_dict(m: ReviewModel) -> Dict[str, Any]:
    """Serialize review model to dict."""
    return {
        "verdict": m.verdict,
        "composite_score": m.composite_score,
        "evidence_completeness": m.evidence_completeness,
        "blockers": list(m.blockers),
        "warnings": list(m.warnings),
        "safety_flags": m.safety_flags,
        "required_artifact_coverage": m.required_artifact_coverage,
        "strategy_robustness_summary": m.strategy_robustness_summary,
        "parameter_fragility_summary": m.parameter_fragility_summary,
        "negative_control_summary": m.negative_control_summary,
        "bootstrap_confidence_summary": m.bootstrap_confidence_summary,
        "regime_warnings": list(m.regime_warnings),
        "portfolio_overlap_risk": m.portfolio_overlap_risk,
        "reproducibility_status": m.reproducibility_status,
    }


def review_model_to_json(m: ReviewModel) -> str:
    """Serialize review model to JSON string."""
    return json.dumps(review_model_to_dict(m), sort_keys=True, indent=2)


# === Helpers ===


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
