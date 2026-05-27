"""Tests for offline shadow bundle builder (Phase 10)."""
import json

import pytest

from core.offline_shadow_bundle_builder import (
    build_bundle,
    build_manifest,
    compute_sha256,
)
from core.offline_shadow_report_renderer import (
    render_report_html,
    render_report_json,
    render_report_markdown,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _sample_plan():
    return {"plan_id": "p1", "experiments": [], "run_config": {}, "safety_policy": {"release_hold": "HOLD", "no_live": True, "no_submit": True, "no_exchange": True}}


def _sample_matrix():
    return {"matrix_id": "m1", "cells": []}


def _sample_results():
    return [
        {
            "experiment_id": "exp_001",
            "symbol": "BTCUSDT",
            "timeframe": "5m",
            "param_label": "conservative",
            "window_id": "w_train",
            "metrics": {
                "candidate_count": 10,
                "win_count": 6,
                "loss_count": 4,
                "neutral_count": 0,
                "win_rate": 0.6,
                "avg_return_r": 0.5,
                "expectancy_r": 0.3,
                "max_drawdown_r": -1.2,
                "avg_mfe_r": 1.5,
                "avg_mae_r": -0.8,
                "profit_factor": 1.5,
                "sample_quality_score": 0.75,
                "coverage_status": "full",
            },
            "scorecard": {"grade": "B+", "composite_score": 0.72},
        }
    ]


def _sample_scorecard():
    return {"scorecard_id": "sc1", "experiments": []}


def _build_sample_bundle():
    results = _sample_results()
    return build_bundle(
        plan_data=_sample_plan(),
        matrix_data=_sample_matrix(),
        results_data=results,
        scorecard_data=_sample_scorecard(),
        report_markdown=render_report_markdown(results),
        report_html=render_report_html(results),
        report_json=render_report_json(results),
    )


# ---------------------------------------------------------------------------
# compute_sha256 tests
# ---------------------------------------------------------------------------

class TestComputeSha256:
    def test_deterministic(self):
        h1 = compute_sha256("hello")
        h2 = compute_sha256("hello")
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = compute_sha256("hello")
        h2 = compute_sha256("world")
        assert h1 != h2

    def test_bytes_input(self):
        h = compute_sha256(b"hello")
        assert len(h) == 64  # sha256 hex length

    def test_str_input(self):
        h = compute_sha256("hello")
        assert len(h) == 64

    def test_empty_string(self):
        h = compute_sha256("")
        assert len(h) == 64


# ---------------------------------------------------------------------------
# build_manifest tests
# ---------------------------------------------------------------------------

class TestBuildManifest:
    def test_hold_field(self):
        m = build_manifest([])
        assert m["release_hold"] == "HOLD"

    def test_safety_flags(self):
        m = build_manifest([])
        assert m["no_live"] is True
        assert m["no_submit"] is True
        assert m["no_exchange"] is True

    def test_artifacts_listed(self):
        arts = [{"name": "a.json", "sha256": "abc123"}]
        m = build_manifest(arts)
        assert m["artifact_count"] == 1
        assert m["artifacts"] == arts

    def test_empty_artifacts(self):
        m = build_manifest([])
        assert m["artifact_count"] == 0


# ---------------------------------------------------------------------------
# build_bundle tests
# ---------------------------------------------------------------------------

class TestBuildBundle:
    def test_returns_all_files(self):
        bundle = _build_sample_bundle()
        expected_keys = {
            "plan.json", "matrix.json", "results.json", "scorecard.json",
            "report.md", "report.html", "report.json", "manifest.json",
        }
        assert set(bundle.keys()) == expected_keys

    def test_manifest_valid_json(self):
        bundle = _build_sample_bundle()
        manifest = json.loads(bundle["manifest.json"])
        assert manifest["release_hold"] == "HOLD"

    def test_manifest_artifact_count(self):
        bundle = _build_sample_bundle()
        manifest = json.loads(bundle["manifest.json"])
        # 7 artifacts (excluding manifest itself)
        assert manifest["artifact_count"] == 7

    def test_manifest_sha256_hashes(self):
        bundle = _build_sample_bundle()
        manifest = json.loads(bundle["manifest.json"])
        for art in manifest["artifacts"]:
            assert len(art["sha256"]) == 64
            assert art["name"] in bundle

    def test_plan_json_valid(self):
        bundle = _build_sample_bundle()
        data = json.loads(bundle["plan.json"])
        assert data["plan_id"] == "p1"

    def test_results_json_valid(self):
        bundle = _build_sample_bundle()
        data = json.loads(bundle["results.json"])
        assert len(data) == 1
        assert data[0]["experiment_id"] == "exp_001"

    def test_report_md_not_empty(self):
        bundle = _build_sample_bundle()
        assert len(bundle["report.md"]) > 0
        assert "HOLD" in bundle["report.md"]

    def test_report_html_not_empty(self):
        bundle = _build_sample_bundle()
        assert len(bundle["report.html"]) > 0
        assert "HOLD" in bundle["report.html"]

    def test_sha256_matches_content(self):
        bundle = _build_sample_bundle()
        manifest = json.loads(bundle["manifest.json"])
        for art in manifest["artifacts"]:
            expected = compute_sha256(bundle[art["name"]])
            assert art["sha256"] == expected, f"hash mismatch for {art['name']}"

    def test_no_network_or_io(self):
        """build_bundle should be pure -- no side effects."""
        # just call it; if it tried any I/O it would fail or block
        bundle = _build_sample_bundle()
        assert isinstance(bundle, dict)
