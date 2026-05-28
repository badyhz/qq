#!/usr/bin/env python3
"""Generate deterministic comparison analytics fixtures."""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).parent


def _write(p: Path, d: dict) -> None:
    p.write_text(json.dumps(d, sort_keys=True, indent=2))


def _manifest(seed=424242, **overrides):
    m = {
        "advisory_only": True,
        "deterministic_seed": seed,
        "generated_at": f"seed_{seed}",
        "generated_by": "research_quality_gate_v2",
        "human_review_required": True,
        "no_exchange": True,
        "no_live": True,
        "no_network": True,
        "no_planner_integration": True,
        "no_runtime_integration": True,
        "no_submit": True,
        "quality_gate_version": "v2.0.0",
        "release_hold": "HOLD",
        "strict_mode": True,
        "input_artifact_hashes": {},
        "output_artifact_hashes": {},
        "artifacts": [],
    }
    m.update(overrides)
    return m


def _quality_summary(score=0.85, verdict="PASS", blocks=None, warns=None):
    return {
        "advisory_only": True,
        "composite_score": score,
        "component_scores": {
            "bootstrap": 0.3,
            "data_quality": 1.0,
            "negative_control": 1.0,
            "oos_validation": 1.0,
            "parameter_fragility": 1.0,
            "portfolio_overlap": 1.0,
            "regime": 1.0,
            "split_leakage": 1.0,
            "strategy_robustness": 1.0,
        },
        "confidence_band": {"lower": 0.75, "upper": 0.95},
        "deterministic_seed": 424242,
        "evidence_completeness": 1.0,
        "generated_at": "seed_424242",
        "generated_by": "research_quality_score",
        "hard_blocks": blocks or [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": verdict,
        "warnings": warns or [],
    }


def _bootstrap(verdict="PASS", ci_lower=0.7, ci_upper=0.95):
    return {
        "advisory_only": True,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": verdict,
        "warnings": [],
    }


def _negative_control(verdict="PASS", margin=0.15):
    return {
        "advisory_only": True,
        "baselines": {
            "inverted_signal": {"score": 0.0},
            "random_strategy": {"score": 0.0},
            "shuffled_returns": {"score": 0.0},
        },
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "margin": margin,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": verdict,
        "warnings": [],
    }


def _regime(verdict="PASS", warns=None, concentration=0.4):
    return {
        "advisory_only": True,
        "concentration": concentration,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "regimes": {},
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": verdict,
        "warnings": warns or [],
    }


def _portfolio_overlap(verdict="PASS", crowding=0.3, pairs=None):
    return {
        "advisory_only": True,
        "crowding": crowding,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "pairs": pairs or [],
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": verdict,
        "warnings": [],
    }


def _param_fragility(verdict="PASS", fragility=0.2):
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "fragility": fragility,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "strategies": {},
        "verdict": verdict,
        "warnings": [],
    }


def _stability(verdict="PASS", stability_score=0.75):
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "stability_score": stability_score,
        "verdict": verdict,
        "warnings": [],
    }


def _reproducibility(verdict="PASS"):
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "human_review_required": True,
        "input_artifact_hashes": {"results.json": "abc123"},
        "output_artifact_hashes": {"quality_gate_summary.json": "def456"},
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "strict": True,
        "verdict": verdict,
    }


def _promotion(verdict="PASS", blocks=None, warns=None):
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": blocks or [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": verdict,
        "warnings": warns or [],
    }


def _robustness(verdict="PASS", score=0.85):
    return {
        "advisory_only": True,
        "composite_score": score,
        "component_scores": {},
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": verdict,
        "warnings": [],
    }


def _report_quality(verdict="PASS"):
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "sections_present": ["summary", "metrics", "regression"],
        "verdict": verdict,
        "warnings": [],
    }


def _artifact_index():
    return {
        "schema_version": "1.0.0",
        "generated_at": "seed_424242",
        "total_artifacts": 1,
        "present_count": 1,
        "artifacts": [],
    }


def _oos():
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": "PASS",
        "warnings": [],
    }


def _split_leakage():
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": "PASS",
        "warnings": [],
    }


def _data_quality():
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": "PASS",
        "warnings": [],
    }


def _param_sensitivity():
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": "PASS",
        "warnings": [],
    }


def _portfolio_robustness():
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": "PASS",
        "warnings": [],
    }


def _correlation_proxy():
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": "PASS",
        "warnings": [],
    }


def _random_strategy():
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": "PASS",
        "warnings": [],
    }


def _shuffled_returns():
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": "PASS",
        "warnings": [],
    }


def _inverted_signal():
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": "PASS",
        "warnings": [],
    }


def _regime_failure():
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": "PASS",
        "warnings": [],
    }


def _rerun_diff():
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "verdict": "PASS",
        "warnings": [],
    }


def _strategy_robustness():
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "strategies": {},
        "verdict": "PASS",
        "warnings": [],
    }


def _param_stability():
    return {
        "advisory_only": True,
        "deterministic_seed": 424242,
        "generated_at": "seed_424242",
        "hard_blocks": [],
        "human_review_required": True,
        "release_hold": "HOLD",
        "schema_version": "1.0.0",
        "stability_score": 0.75,
        "verdict": "PASS",
        "warnings": [],
    }


def _write_bundle(d: Path, manifest=None, qgs=None, **kw):
    """Write a complete bundle directory."""
    d.mkdir(parents=True, exist_ok=True)
    _write(d / "manifest.json", manifest or _manifest())
    _write(d / "quality_gate_summary.json", qgs or _quality_summary())
    _write(d / "bootstrap_report.json", _bootstrap(**kw.get("bootstrap", {})))
    _write(d / "negative_control_report.json", _negative_control(**kw.get("nc", {})))
    _write(d / "regime_breakdown.json", _regime(**kw.get("regime", {})))
    _write(d / "portfolio_overlap_risk.json", _portfolio_overlap(**kw.get("overlap", {})))
    _write(d / "parameter_fragility_report.json", _param_fragility(**kw.get("fragility", {})))
    _write(d / "parameter_stability.json", _stability(**kw.get("stability", {})))
    _write(d / "reproducibility_manifest.json", _reproducibility(**kw.get("repro", {})))
    _write(d / "promotion_gate_v2.json", _promotion(**kw.get("promotion", {})))
    _write(d / "robustness_scorecard.json", _robustness(**kw.get("robustness", {})))
    _write(d / "report_quality_check.json", _report_quality(**kw.get("rqc", {})))
    _write(d / "artifact_index.json", _artifact_index())
    _write(d / "oos_validation_report.json", _oos())
    _write(d / "split_leakage_report.json", _split_leakage())
    _write(d / "data_quality_deep_audit.json", _data_quality())
    _write(d / "parameter_sensitivity_ranking.json", _param_sensitivity())
    _write(d / "portfolio_robustness_report.json", _portfolio_robustness())
    _write(d / "correlation_proxy_report.json", _correlation_proxy())
    _write(d / "random_strategy_baseline.json", _random_strategy())
    _write(d / "shuffled_returns_baseline.json", _shuffled_returns())
    _write(d / "inverted_signal_baseline.json", _inverted_signal())
    _write(d / "regime_failure_report.json", _regime_failure())
    _write(d / "rerun_diff_report.json", _rerun_diff())
    _write(d / "strategy_robustness_report.json", _strategy_robustness())


# === artifact_browser_baseline ===
_write_bundle(BASE / "artifact_browser_baseline")

# === artifact_browser_candidate_improved ===
_write_bundle(
    BASE / "artifact_browser_candidate_improved",
    qgs=_quality_summary(score=0.90, warns=[]),
    bootstrap=dict(ci_lower=0.80, ci_upper=0.95),
    nc=dict(margin=0.20),
    regime=dict(concentration=0.3),
    overlap=dict(crowding=0.2),
    fragility=dict(fragility=0.15),
    stability=dict(stability_score=0.85),
)

# === artifact_browser_candidate_regressed ===
_write_bundle(
    BASE / "artifact_browser_candidate_regressed",
    qgs=_quality_summary(score=0.65, verdict="PARTIAL", blocks=["score_below_threshold"], warns=["bootstrap_below_threshold", "fragility_warning"]),
    bootstrap=dict(ci_lower=0.50, ci_upper=0.75),
    nc=dict(margin=0.05),
    regime=dict(concentration=0.6, warns=["high_concentration"]),
    overlap=dict(crowding=0.5),
    fragility=dict(fragility=0.35),
    stability=dict(stability_score=0.55),
)

# === artifact_browser_invalid_safety ===
_write_bundle(
    BASE / "artifact_browser_invalid_safety",
    manifest=_manifest(no_network=False, advisory_only=False, human_review_required=False),
)

# === artifact_browser_corrupted ===
d = BASE / "artifact_browser_corrupted"
d.mkdir(parents=True, exist_ok=True)
_write_bundle(d)
(d / "quality_gate_summary.json").write_text("NOT JSON{")

# === quality_gate_baseline ===
_write_bundle(BASE / "quality_gate_baseline")

# === quality_gate_candidate_changed ===
_write_bundle(
    BASE / "quality_gate_candidate_changed",
    qgs=_quality_summary(score=0.78, verdict="PARTIAL", warns=["new_warning"]),
    nc=dict(margin=0.08),
    fragility=dict(fragility=0.30),
)

# === quality_gate_series_three_runs/run1 ===
_write_bundle(
    BASE / "quality_gate_series_three_runs" / "run1",
    qgs=_quality_summary(score=0.80),
    nc=dict(margin=0.12),
    fragility=dict(fragility=0.25),
    bootstrap=dict(ci_lower=0.70, ci_upper=0.90),
)

# === quality_gate_series_three_runs/run2 ===
_write_bundle(
    BASE / "quality_gate_series_three_runs" / "run2",
    qgs=_quality_summary(score=0.85),
    nc=dict(margin=0.15),
    fragility=dict(fragility=0.20),
    bootstrap=dict(ci_lower=0.75, ci_upper=0.92),
)

# === quality_gate_series_three_runs/run3 ===
_write_bundle(
    BASE / "quality_gate_series_three_runs" / "run3",
    qgs=_quality_summary(score=0.90),
    nc=dict(margin=0.18),
    fragility=dict(fragility=0.15),
    bootstrap=dict(ci_lower=0.80, ci_upper=0.95),
)

print("Fixtures generated.")
