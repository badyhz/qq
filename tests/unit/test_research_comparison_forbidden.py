"""Tests for forbidden imports in comparison analytics code.

Safety tests. Offline only. No network.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.research_no_network_import_guard import scan_file_forbidden_imports

CORE = Path(__file__).resolve().parent.parent.parent / "core"
SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"

COMPARISON_FILES = (
    CORE / "research_bundle_series.py",
    CORE / "research_comparison_metrics.py",
    CORE / "research_comparison_pairwise.py",
    CORE / "research_trend_engine.py",
    CORE / "research_comparison_regression.py",
    CORE / "research_comparison_scorecard.py",
    CORE / "research_comparison_report.py",
    CORE / "research_comparison_manifest.py",
)

COMPARISON_SCRIPTS = (
    SCRIPTS / "build_research_comparison_analytics.py",
    SCRIPTS / "compare_research_quality_series.py",
    SCRIPTS / "render_research_comparison_report.py",
)


class TestForbiddenImports:
    """Test that comparison code has no forbidden imports."""

    @pytest.mark.parametrize("file_path", COMPARISON_FILES, ids=lambda p: p.name)
    def test_core_no_forbidden_imports(self, file_path):
        """Test core comparison modules have no forbidden imports."""
        violations = scan_file_forbidden_imports(file_path)
        assert len(violations) == 0, f"Forbidden imports in {file_path.name}: {violations}"

    @pytest.mark.parametrize("file_path", COMPARISON_SCRIPTS, ids=lambda p: p.name)
    def test_script_no_forbidden_imports(self, file_path):
        """Test comparison scripts have no forbidden imports."""
        violations = scan_file_forbidden_imports(file_path)
        assert len(violations) == 0, f"Forbidden imports in {file_path.name}: {violations}"

    def test_no_requests_import(self):
        """Test no requests/httpx/aiohttp imports."""
        for f in list(COMPARISON_FILES) + list(COMPARISON_SCRIPTS):
            content = f.read_text()
            for forbidden in ("import requests", "import httpx", "import aiohttp",
                              "from requests", "from httpx", "from aiohttp"):
                assert forbidden not in content, f"{forbidden} found in {f.name}"

    def test_no_websocket_import(self):
        """Test no websocket imports."""
        for f in list(COMPARISON_FILES) + list(COMPARISON_SCRIPTS):
            content = f.read_text()
            assert "import websocket" not in content
            assert "from websocket" not in content

    def test_no_exchange_import(self):
        """Test no exchange/live/testnet imports."""
        for f in list(COMPARISON_FILES) + list(COMPARISON_SCRIPTS):
            content = f.read_text()
            for forbidden in ("import exchange", "from exchange",
                              "import live_submit", "import testnet_submit",
                              "import binance", "from binance"):
                assert forbidden not in content, f"{forbidden} found in {f.name}"
