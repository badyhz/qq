"""Tests for research quality acceptance — T5261-T5270.

CLI args, strict mode, failure state tests.
"""
from __future__ import annotations

import json
import pytest
import tempfile
from pathlib import Path
from core.research_quality_gate_v2 import run_quality_gate
from core.research_quality_contract import RELEASE_HOLD_VALUE


class TestAcceptanceNormal:
    def test_run_quality_gate(self):
        with tempfile.TemporaryDirectory() as ind, tempfile.TemporaryDirectory() as outd:
            # Create minimal workbench input
            input_dir = Path(ind)
            (input_dir / "results.json").write_text(json.dumps({
                "results": [
                    {"strategy_id": "breakout", "symbol": "BTCUSDT", "timeframe": "5m",
                     "score": 0.5, "trade_count": 10, "parameter_set_id": "p1"},
                    {"strategy_id": "momentum", "symbol": "BTCUSDT", "timeframe": "5m",
                     "score": 0.3, "trade_count": 8, "parameter_set_id": "p2"},
                ],
                "total_rows": 2, "evaluated_rows": 2, "skipped_rows": 0, "warnings": [],
            }))
            (input_dir / "comparison.json").write_text(json.dumps({}))
            (input_dir / "portfolio_summary.json").write_text(json.dumps({}))
            (input_dir / "promotion_recommendations.json").write_text(json.dumps([]))
            (input_dir / "parameter_search.json").write_text(json.dumps({}))
            (input_dir / "strategy_registry.json").write_text(json.dumps({}))
            (input_dir / "matrix.json").write_text(json.dumps({}))

            result = run_quality_gate(
                input_dir, Path(outd), seed=42, strict=True, release_hold="HOLD"
            )
            assert result["verdict"] in ("PASS", "PARTIAL", "FAIL")
            assert result["artifacts_written"] > 0


class TestAcceptanceEdge:
    def test_non_hold_raises(self):
        with tempfile.TemporaryDirectory() as ind, tempfile.TemporaryDirectory() as outd:
            with pytest.raises(ValueError):
                run_quality_gate(Path(ind), Path(outd), release_hold="BAD")


class TestAcceptanceSafetyBoundary:
    def test_gate_safety(self):
        with tempfile.TemporaryDirectory() as ind, tempfile.TemporaryDirectory() as outd:
            input_dir = Path(ind)
            (input_dir / "results.json").write_text(json.dumps({"results": [], "total_rows": 0, "evaluated_rows": 0, "skipped_rows": 0, "warnings": []}))
            (input_dir / "comparison.json").write_text(json.dumps({}))

            result = run_quality_gate(input_dir, Path(outd), seed=42)
            # Check manifest
            manifest = json.loads((Path(outd) / "manifest.json").read_text())
            assert manifest["release_hold"] == "HOLD"
            assert manifest["advisory_only"] is True
            assert manifest["human_review_required"] is True
