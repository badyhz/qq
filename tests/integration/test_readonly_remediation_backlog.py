"""Integration test: readonly remediation backlog."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_scope_audit.remediation_backlog import (
    create_backlog, count_by_priority
)


def test_create_backlog():
    backlog = create_backlog()
    assert backlog.backlog_id.startswith("RBL_")
    assert len(backlog.items) == 6


def test_p0_safety_item():
    backlog = create_backlog()
    p0_items = [i for i in backlog.items if i.priority == "P0"]
    assert len(p0_items) == 1
    assert p0_items[0].safe_to_auto_execute is True


def test_priority_distribution():
    backlog = create_backlog()
    by_pri = count_by_priority(backlog)
    assert by_pri["P0"] == 1
    assert by_pri["P2"] >= 2
    assert by_pri["P3"] >= 2


def test_no_high_priority_safety_gaps():
    backlog = create_backlog()
    p1_items = [i for i in backlog.items if i.priority == "P1"]
    assert len(p1_items) == 0


def test_render_report():
    from src.runtime_integrations.testnet_readonly_scope_audit.remediation_backlog import render_report
    backlog = create_backlog()
    report = render_report(backlog)
    assert "READONLY_REMEDIATION_BACKLOG_READY" in report


def test_rem002_expanded():
    backlog = create_backlog()
    rem002 = [i for i in backlog.items if i.task_id == "REM_002"][0]
    assert "Expanded in T325001-T335000" in rem002.recommended_fix


def test_rem003_split_completed():
    backlog = create_backlog()
    rem003 = [i for i in backlog.items if i.task_id == "REM_003"][0]
    assert "Test split completed in T325001-T335000" in rem003.recommended_fix


def test_rem004_split_completed():
    backlog = create_backlog()
    rem004 = [i for i in backlog.items if i.task_id == "REM_004"][0]
    assert "Test split completed in T325001-T335000" in rem004.recommended_fix


def test_rem005_de_facto_registry():
    backlog = create_backlog()
    rem005 = [i for i in backlog.items if i.task_id == "REM_005"][0]
    assert "De facto spec registry created in T325001-T335000" in rem005.recommended_fix
