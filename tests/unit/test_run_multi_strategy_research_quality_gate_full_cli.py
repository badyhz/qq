"""Tests for full quality gate CLI — T8721-T8760.

Full CLI arg matrix, fail-fast, strict tests.
"""
from __future__ import annotations

import json
import pytest
import tempfile
from pathlib import Path
from core.research_quality_gate_v2 import run_quality_gate
from core.research_quality_manifest import REQUIRED_ARTIFACTS


class TestFullCLINormal:
    def test_full_run(self):
        with tempfile.TemporaryDirectory() as ind, tempfile.TemporaryDirectory() as outd:
            input_dir = Path(ind)
            (input_dir / "results.json").write_text(json.dumps({
                "results": [
                    {"strategy_id": "breakout", "symbol": "BTCUSDT", "timeframe": "5m",
                     "score": 0.5, "trade_count": 10, "parameter_set_id": "p1"},
                ],
                "total_rows": 1, "evaluated_rows": 1, "skipped_rows": 0, "warnings": [],
            }))
            (input_dir / "comparison.json").write_text(json.dumps({}))
            (input_dir / "portfolio_summary.json").write_text(json.dumps({}))
            (input_dir / "promotion_recommendations.json").write_text(json.dumps([]))
            (input_dir / "parameter_search.json").write_text(json.dumps({}))
            (input_dir / "strategy_registry.json").write_text(json.dumps({}))
            (input_dir / "matrix.json").write_text(json.dumps({}))

            result = run_quality_gate(input_dir, Path(outd), seed=424242, strict=True)
            assert result["artifacts_written"] > 0

            # Check key artifacts exist
            output_dir = Path(outd)
            for name in ["quality_gate_summary.json", "manifest.json", "report.md", "report.html"]:
                assert (output_dir / name).exists(), f"Missing {name}"


class TestFullCLISafetyBoundary:
    def test_manifest_safety(self):
        with tempfile.TemporaryDirectory() as ind, tempfile.TemporaryDirectory() as outd:
            input_dir = Path(ind)
            (input_dir / "results.json").write_text(json.dumps({"results": [], "total_rows": 0, "evaluated_rows": 0, "skipped_rows": 0, "warnings": []}))
            (input_dir / "comparison.json").write_text(json.dumps({}))

            run_quality_gate(input_dir, Path(outd), seed=424242)

            manifest = json.loads((Path(outd) / "manifest.json").read_text())
            assert manifest["release_hold"] == "HOLD"
            assert manifest["advisory_only"] is True
            assert manifest["human_review_required"] is True
            assert manifest["no_live"] is True
            assert manifest["no_submit"] is True
            assert manifest["no_exchange"] is True
            assert manifest["no_network"] is True
