import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_one_shot_submit_lifecycle_closeout_snapshot_v1 import generate_closeout_snapshot


def replay(verdict="PASS", artifact_count=7):
    return {
        "verdict": verdict,
        "artifact_count": artifact_count,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
    }


def guard(verdict="PASS"):
    return {
        "verdict": verdict,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
    }


def dashboard(verdict="PASS", status="CLOSED_HEALTHY"):
    return {
        "verdict": verdict,
        "lifecycle_status": status,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
    }


def final_phase(decision="CLOSED", max_submit_count=0, submit_allowed=False):
    return {
        "decision": decision,
        "max_submit_count": max_submit_count,
        "submit_allowed": submit_allowed,
        "cancel_allowed": False,
        "flatten_allowed": False,
    }


def test_closed_snapshot_pass():
    r = generate_closeout_snapshot(replay(), guard(), dashboard(), final_phase())
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["lifecycle_status"] == "CLOSED_HEALTHY"


def test_monitor_partial():
    r = generate_closeout_snapshot(
        replay(),
        guard("PARTIAL"),
        dashboard("PARTIAL", "MONITOR"),
        final_phase("MONITOR"),
    )
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"
    assert r["lifecycle_status"] == "MONITOR"


def test_rollback_fail():
    r = generate_closeout_snapshot(
        replay("FAIL"),
        guard("FAIL"),
        dashboard("FAIL", "ROLLBACK_REVIEW"),
        final_phase("REQUIRE_HUMAN_ROLLBACK_REVIEW"),
    )
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"


def test_action_allowed_fail():
    r = generate_closeout_snapshot(replay(), guard(), dashboard(), final_phase(submit_allowed=True))
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"


def test_max_submit_count_zero():
    r = generate_closeout_snapshot(replay(), guard(), dashboard(), final_phase())
    assert r["max_submit_count"] == 0
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False
