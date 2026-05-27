"""Tests for core/offline_shadow_evaluator.py."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from core.offline_shadow_evaluator import evaluate_experiment


def _write_fixture(fixture_dir: Path, run_id: str, outcomes: list[dict]) -> None:
    (fixture_dir / f"{run_id}.json").write_text(
        json.dumps(outcomes), encoding="utf-8"
    )


def _matrix(*run_ids: str, experiment_id: str = "exp-001") -> dict:
    return {
        "experiment_id": experiment_id,
        "runs": [{"run_id": rid} for rid in run_ids],
    }


def test_empty_matrix() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = evaluate_experiment({"runs": []}, tmp)
        assert result["run_count"] == 0
        assert result["runs"] == []


def test_single_run_metrics_present() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _write_fixture(Path(tmp), "run-1", [{"return_r": 1.0}, {"return_r": -0.5}])
        result = evaluate_experiment(_matrix("run-1"), tmp)
        assert result["run_count"] == 1
        run = result["runs"][0]
        assert run["run_id"] == "run-1"
        assert run["outcome_count"] == 2
        assert "metrics" in run
        assert run["metrics"]["candidate_count"] == 2


def test_multiple_runs_count() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        _write_fixture(p, "a", [{"return_r": 1.0}])
        _write_fixture(p, "b", [{"return_r": -1.0}])
        _write_fixture(p, "c", [{"return_r": 0.5}])
        result = evaluate_experiment(_matrix("a", "b", "c"), tmp)
        assert result["run_count"] == 3
        ids = [r["run_id"] for r in result["runs"]]
        assert ids == ["a", "b", "c"]


def test_missing_fixture_returns_empty_outcomes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = evaluate_experiment(_matrix("nonexistent"), tmp)
        assert result["run_count"] == 1
        assert result["runs"][0]["outcome_count"] == 0
        assert result["runs"][0]["metrics"]["coverage_status"] == "empty"


def test_deterministic_output() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        _write_fixture(p, "r1", [{"return_r": 2.0}, {"return_r": -1.0}])
        _write_fixture(p, "r2", [{"return_r": 0.5}])
        m = _matrix("r1", "r2")
        r1 = evaluate_experiment(m, tmp)
        r2 = evaluate_experiment(m, tmp)
        assert r1 == r2


def test_experiment_id_preserved() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        _write_fixture(Path(tmp), "x", [{"return_r": 1.0}])
        result = evaluate_experiment(
            _matrix("x", experiment_id="my-exp-42"), tmp
        )
        assert result["experiment_id"] == "my-exp-42"


def test_wrapped_outcome_format() -> None:
    """Outcomes file can be {"outcomes": [...]} instead of bare list."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "wrap.json"
        path.write_text(
            json.dumps({"outcomes": [{"return_r": 1.0}, {"return_r": 2.0}]}),
            encoding="utf-8",
        )
        result = evaluate_experiment(_matrix("wrap"), tmp)
        assert result["runs"][0]["outcome_count"] == 2


def test_corrupt_json_returns_empty() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "bad.json").write_text("NOT JSON {{{", encoding="utf-8")
        result = evaluate_experiment(_matrix("bad"), tmp)
        assert result["runs"][0]["outcome_count"] == 0
