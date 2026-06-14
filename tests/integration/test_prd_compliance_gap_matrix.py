"""Integration test: PRD compliance gap matrix."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_scope_audit.prd_compliance_gap_matrix import (
    create_matrix, count_by_severity, count_blocking
)


def test_create_matrix():
    matrix = create_matrix()
    assert matrix.matrix_id.startswith("GM_")
    assert len(matrix.gaps) == 32


def test_no_blocking_gaps():
    matrix = create_matrix()
    assert count_blocking(matrix) == 0


def test_no_high_severity():
    matrix = create_matrix()
    by_sev = count_by_severity(matrix)
    assert by_sev.get("HIGH", 0) == 0


def test_all_stages_covered():
    matrix = create_matrix()
    stages = {g.stage_id for g in matrix.gaps}
    for i in range(1, 7):
        assert f"STG_RO_{i:03d}" in stages
    assert "ALL" in stages


def test_render_report():
    from src.runtime_integrations.testnet_readonly_scope_audit.prd_compliance_gap_matrix import render_report
    matrix = create_matrix()
    report = render_report(matrix)
    assert "PRD_COMPLIANCE_GAP_REPORT_READY" in report
