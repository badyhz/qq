"""Tests for prd_queue_closeout_packet — T871."""

from core.prd_queue_closeout_packet import (
    PrdQueueCloseoutPacket,
    build_prd_queue_closeout_packet,
    queue_closeout_packet_to_dict,
    queue_closeout_packet_to_markdown,
)


def test_closeout_has_hard_stop_t872():
    p = build_prd_queue_closeout_packet()
    assert p.hard_stop_task == "T872"


def test_next_task_allowed_false_by_default():
    p = build_prd_queue_closeout_packet()
    assert p.next_task_allowed is False


def test_next_task_allowed_false_unless_human_instruction():
    p = build_prd_queue_closeout_packet(next_task_allowed=False)
    assert p.next_task_allowed is False
    p2 = build_prd_queue_closeout_packet(next_task_allowed=True)
    assert p2.next_task_allowed is True


def test_deterministic_output():
    p1 = build_prd_queue_closeout_packet()
    p2 = build_prd_queue_closeout_packet()
    assert p1 == p2
    assert queue_closeout_packet_to_dict(p1) == queue_closeout_packet_to_dict(p2)


def test_packet_is_frozen():
    p = build_prd_queue_closeout_packet()
    try:
        p.queue_range = "T999"  # type: ignore[misc]
        assert False, "should be frozen"
    except AttributeError:
        pass


def test_completed_tasks_default():
    p = build_prd_queue_closeout_packet()
    assert len(p.completed_tasks) == 8
    assert p.completed_tasks[0] == "T865"
    assert p.completed_tasks[-1] == "T872"


def test_to_dict_keys():
    p = build_prd_queue_closeout_packet()
    d = queue_closeout_packet_to_dict(p)
    expected = {
        "queue_range", "completed_tasks", "expected_artifacts",
        "validation_verdict", "safety_verdict", "final_status",
        "hard_stop_task", "next_task_allowed", "notes",
    }
    assert set(d.keys()) == expected


def test_to_markdown_contains_hard_stop():
    p = build_prd_queue_closeout_packet()
    md = queue_closeout_packet_to_markdown(p)
    assert "T872" in md
    assert "hard stop" in md.lower()


def test_custom_values():
    p = build_prd_queue_closeout_packet(
        queue_range="T900-T910",
        expected_artifacts=11,
        final_status="PARTIAL",
    )
    assert p.queue_range == "T900-T910"
    assert p.expected_artifacts == 11
    assert p.final_status == "PARTIAL"
