"""Integration test: testnet read-only scope audit suite."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_scope_audit.stage_inventory import create_inventory
from src.runtime_integrations.testnet_readonly_scope_audit.prd_compliance_gap_matrix import create_matrix, count_blocking
from src.runtime_integrations.testnet_readonly_scope_audit.suite_depth_review import create_review, count_by_rating
from src.runtime_integrations.testnet_readonly_scope_audit.remediation_backlog import create_backlog, count_by_priority
from src.runtime_integrations.testnet_readonly_scope_audit.scope_audit_safety_regression import run_regression


def test_stage_inventory_ready():
    inventory = create_inventory()
    assert len(inventory.stages) == 6


def test_gap_matrix_ready():
    matrix = create_matrix()
    assert count_blocking(matrix) == 0


def test_suite_depth_review_ready():
    review = create_review()
    by_rating = count_by_rating(review)
    assert by_rating.get("NEEDS_FOLLOWUP", 0) == 0


def test_remediation_backlog_ready():
    backlog = create_backlog()
    by_pri = count_by_priority(backlog)
    assert "P0" in by_pri


def test_safety_regression_clean():
    items = run_regression()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0, f"Safety regression failures: {[i.check_id for i in failed]}"
