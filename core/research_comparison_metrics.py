"""Research comparison metrics — extract comparable metrics from bundles.

Program B: Metric Extraction.
Extract standardized metrics from each bundle for comparison.

No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.research_bundle_series import BundleRecord


@dataclass(frozen=True)
class ExtractedMetrics:
    """Standardized metrics extracted from a bundle."""
    label: str
    verdict: str
    composite_score: float
    evidence_completeness: float
    stability_score: float
    parameter_fragility: float
    overlap_risk: float
    negative_control_margin: float
    bootstrap_ci_width: float
    bootstrap_worst_case: float
    regime_concentration_warning_count: int
    portfolio_crowding_score: float
    portfolio_degradation_score: float
    blocker_count: int
    warning_count: int
    required_artifact_coverage: float
    reproducibility_status: str
    release_hold: str
    advisory_only: bool
    human_review_required: bool
    no_live: bool
    no_submit: bool
    no_exchange: bool
    no_network: bool
    quality_gate_version: str
    deterministic_seed: int


def extract_metrics(record: BundleRecord) -> ExtractedMetrics:
    """Extract standardized metrics from a bundle record."""
    m = record.manifest
    qgs = record.quality_summary
    bundle_path = Path(record.path)

    # Detect format: artifact browser has nested summaries in review_model
    is_browser_format = "safety_flags" in qgs

    # Try to load additional files from the bundle path
    bootstrap = _load_json(bundle_path / "bootstrap_report.json")
    nc = _load_json(bundle_path / "negative_control_report.json")
    regime = _load_json(bundle_path / "regime_breakdown.json")
    overlap = _load_json(bundle_path / "portfolio_overlap_risk.json")
    fragility = _load_json(bundle_path / "parameter_fragility_report.json")
    stability = _load_json(bundle_path / "parameter_stability.json")
    repro = _load_json(bundle_path / "reproducibility_manifest.json")

    if is_browser_format:
        # Artifact browser format: review_model.json has nested summaries
        boot_summary = qgs.get("bootstrap_confidence_summary", {})
        nc_summary = qgs.get("negative_control_summary", {})
        frag_summary = qgs.get("parameter_fragility_summary", {})
        overlap_summary = qgs.get("portfolio_overlap_risk", {})

        bootstrap = boot_summary if boot_summary else bootstrap
        nc = nc_summary if nc_summary else nc
        fragility = frag_summary if frag_summary else fragility
        overlap = overlap_summary if overlap_summary else overlap

    # Composite score
    composite_score = qgs.get("composite_score", 0.0)

    # Evidence completeness
    evidence_completeness = qgs.get("evidence_completeness", 0.0)

    # Stability score
    stability_score = stability.get("stability_score", 0.0)

    # Parameter fragility
    parameter_fragility = fragility.get("fragility", 0.0)

    # Overlap risk / crowding
    crowding = overlap.get("crowding", 0.0)

    # Negative control margin
    nc_margin = nc.get("margin", 0.0)

    # Bootstrap CI
    ci_lower = bootstrap.get("ci_lower", 0.0)
    ci_upper = bootstrap.get("ci_upper", 0.0)
    bootstrap_ci_width = ci_upper - ci_lower
    bootstrap_worst_case = ci_lower

    # Regime warnings
    if is_browser_format:
        regime_warns = tuple(qgs.get("regime_warnings", []))
    else:
        regime_warns = regime.get("warnings", [])
    regime_concentration = regime.get("concentration", 0.0)

    # Blockers and warnings
    blockers = qgs.get("hard_blocks", []) if not is_browser_format else qgs.get("blockers", [])
    warnings = qgs.get("warnings", [])

    # Reproducibility
    if is_browser_format:
        repro_status = qgs.get("reproducibility_status", "UNKNOWN")
    else:
        repro_status = repro.get("verdict", "UNKNOWN")

    # Release hold
    release_hold = m.get("release_hold", "UNKNOWN")
    if release_hold == "UNKNOWN" and is_browser_format:
        sf = qgs.get("safety_flags", {})
        release_hold = "HOLD" if sf.get("release_hold_is_HOLD", False) else "UNKNOWN"

    # Safety flags - handle both manifest formats
    if is_browser_format:
        sf = qgs.get("safety_flags", {})
        advisory_only = bool(sf.get("advisory_only", False))
        human_review_required = bool(sf.get("human_review_required", False))
        no_live = bool(sf.get("no_live", False))
        no_submit = bool(sf.get("no_submit", False))
        no_exchange = bool(sf.get("no_exchange", False))
        no_network = bool(sf.get("no_network", False))
    else:
        advisory_only = bool(m.get("advisory_only", False))
        human_review_required = bool(m.get("human_review_required", False))
        no_live = bool(m.get("no_live", False))
        no_submit = bool(m.get("no_submit", False))
        no_exchange = bool(m.get("no_exchange", False))
        no_network = bool(m.get("no_network", False))

    return ExtractedMetrics(
        label=record.label,
        verdict=qgs.get("verdict", "UNKNOWN"),
        composite_score=composite_score,
        evidence_completeness=evidence_completeness,
        stability_score=stability_score,
        parameter_fragility=parameter_fragility,
        overlap_risk=crowding,
        negative_control_margin=nc_margin,
        bootstrap_ci_width=bootstrap_ci_width,
        bootstrap_worst_case=bootstrap_worst_case,
        regime_concentration_warning_count=len(regime_warns),
        portfolio_crowding_score=crowding,
        portfolio_degradation_score=0.0,  # derived from overlap
        blocker_count=len(blockers),
        warning_count=len(warnings),
        required_artifact_coverage=1.0 if record.json_parse_ok else 0.0,
        reproducibility_status=repro_status,
        release_hold=release_hold,
        advisory_only=advisory_only,
        human_review_required=human_review_required,
        no_live=no_live,
        no_submit=no_submit,
        no_exchange=no_exchange,
        no_network=no_network,
        quality_gate_version=m.get("quality_gate_version", ""),
        deterministic_seed=m.get("deterministic_seed", 0),
    )


def extract_metrics_from_records(
    records: Tuple[BundleRecord, ...],
) -> Tuple[ExtractedMetrics, ...]:
    """Extract metrics from all bundle records."""
    return tuple(extract_metrics(r) for r in records)


def metrics_to_dict(m: ExtractedMetrics) -> Dict[str, Any]:
    """Serialize extracted metrics to dict."""
    return {
        "label": m.label,
        "verdict": m.verdict,
        "composite_score": m.composite_score,
        "evidence_completeness": m.evidence_completeness,
        "stability_score": m.stability_score,
        "parameter_fragility": m.parameter_fragility,
        "overlap_risk": m.overlap_risk,
        "negative_control_margin": m.negative_control_margin,
        "bootstrap_ci_width": m.bootstrap_ci_width,
        "bootstrap_worst_case": m.bootstrap_worst_case,
        "regime_concentration_warning_count": m.regime_concentration_warning_count,
        "portfolio_crowding_score": m.portfolio_crowding_score,
        "portfolio_degradation_score": m.portfolio_degradation_score,
        "blocker_count": m.blocker_count,
        "warning_count": m.warning_count,
        "required_artifact_coverage": m.required_artifact_coverage,
        "reproducibility_status": m.reproducibility_status,
        "release_hold": m.release_hold,
        "advisory_only": m.advisory_only,
        "human_review_required": m.human_review_required,
        "no_live": m.no_live,
        "no_submit": m.no_submit,
        "no_exchange": m.no_exchange,
        "no_network": m.no_network,
        "quality_gate_version": m.quality_gate_version,
        "deterministic_seed": m.deterministic_seed,
    }


def build_extracted_metrics_json(
    metrics: Tuple[ExtractedMetrics, ...],
    generated_at: str = "deterministic",
) -> Dict[str, Any]:
    """Build extracted_metrics.json content."""
    return {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "bundle_count": len(metrics),
        "metrics": [metrics_to_dict(m) for m in metrics],
    }


def _load_json(path: Path) -> Dict[str, Any]:
    """Load JSON file, return empty dict on failure."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError):
        return {}
