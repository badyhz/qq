import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_one_shot_submit_lifecycle_final_archive_phase_control_report_v1 import (
    generate_final_archive_phase_control_report,
)


def replay(verdict="PASS"):
    return {
        "verdict": verdict,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "max_submit_count": 0,
    }


def guard(verdict="PASS"):
    return {
        "verdict": verdict,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "max_submit_count": 0,
    }


def dashboard(verdict="PASS"):
    return {
        "verdict": verdict,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "max_submit_count": 0,
    }


def snapshot(verdict="PASS", status="CLOSED_HEALTHY"):
    return {
        "verdict": verdict,
        "lifecycle_status": status,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
        "max_submit_count": 0,
    }


def test_archived_closed():
    r = generate_final_archive_phase_control_report(replay(), guard(), dashboard(), snapshot())
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["decision"] == "ARCHIVED_CLOSED"


def test_archived_monitor():
    r = generate_final_archive_phase_control_report(
        replay("PARTIAL"),
        guard("PARTIAL"),
        dashboard("PARTIAL"),
        snapshot("PARTIAL", "MONITOR"),
    )
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "ARCHIVED_MONITOR"


def test_archived_review():
    r = generate_final_archive_phase_control_report(
        replay("PARTIAL"),
        guard("PARTIAL"),
        dashboard("PARTIAL"),
        snapshot("PARTIAL", "REVIEW"),
    )
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "ARCHIVED_REVIEW"


def test_rollback_review():
    r = generate_final_archive_phase_control_report(
        replay("FAIL"),
        guard("FAIL"),
        dashboard("FAIL"),
        snapshot("FAIL", "ROLLBACK_REVIEW"),
    )
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "REQUIRE_HUMAN_ROLLBACK_REVIEW"


def test_stop():
    r = generate_final_archive_phase_control_report(
        replay("FAIL"),
        guard("FAIL"),
        dashboard("FAIL"),
        snapshot("FAIL", "STOP"),
    )
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "STOP"
