"""Tests for prd_control_plane_final_status_report — T872."""

from core.prd_control_plane_final_status_report import (
    PrdControlPlaneFinalStatusReport,
    build_prd_control_plane_final_status_report,
    prd_control_plane_final_status_report_to_dict,
    prd_control_plane_final_status_report_to_markdown,
)


def test_final_status_pass_by_default():
    r = build_prd_control_plane_final_status_report()
    assert r.final_status == "PASS"


def test_hard_stop_is_t872():
    r = build_prd_control_plane_final_status_report()
    assert r.hard_stop == "T872"


def test_completed_count():
    r = build_prd_control_plane_final_status_report()
    assert r.completed_count == 8


def test_deterministic_output():
    r1 = build_prd_control_plane_final_status_report()
    r2 = build_prd_control_plane_final_status_report()
    assert r1 == r2
    d1 = prd_control_plane_final_status_report_to_dict(r1)
    d2 = prd_control_plane_final_status_report_to_dict(r2)
    assert d1 == d2


def test_report_is_frozen():
    r = build_prd_control_plane_final_status_report()
    try:
        r.final_status = "FAIL"  # type: ignore[misc]
        assert False, "should be frozen"
    except AttributeError:
        pass


def test_to_dict_keys():
    r = build_prd_control_plane_final_status_report()
    d = prd_control_plane_final_status_report_to_dict(r)
    expected = {
        "task_range", "completed_count", "test_summary",
        "final_status", "next_safe_phase", "hard_stop", "notes",
    }
    assert set(d.keys()) == expected


def test_to_markdown_contains_status():
    r = build_prd_control_plane_final_status_report()
    md = prd_control_plane_final_status_report_to_markdown(r)
    assert "PASS" in md
    assert "T872" in md
    assert "T873" in md


def test_custom_values():
    r = build_prd_control_plane_final_status_report(
        final_status="PARTIAL",
        completed_count=5,
    )
    assert r.final_status == "PARTIAL"
    assert r.completed_count == 5


def test_task_queue_doc_has_t865_to_t872():
    with open("docs/dev_prd/runtime_governance_task_queue.md") as f:
        content = f.read()
    for t in ["T865", "T866", "T867", "T868", "T869", "T870", "T871", "T872"]:
        assert t in content, f"{t} missing from task queue doc"


def test_task_queue_doc_has_t873_to_t880():
    with open("docs/dev_prd/runtime_governance_task_queue.md") as f:
        content = f.read()
    for t in ["T873", "T874", "T875", "T876", "T877", "T878", "T879", "T880"]:
        assert t in content, f"{t} missing from task queue doc"


def test_t873_to_t880_are_human_review_required():
    with open("docs/dev_prd/runtime_governance_task_queue.md") as f:
        content = f.read()
    for t in ["T873", "T874", "T875", "T876", "T877", "T878", "T879", "T880"]:
        assert "HUMAN_REVIEW_REQUIRED" in content, "missing HUMAN_REVIEW_REQUIRED marker"
        assert "NOT_STARTED" in content, "missing NOT_STARTED marker"
