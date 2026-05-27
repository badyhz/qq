from core.runtime_governance_readonly_final_closeout_doc import (
    build_readonly_final_closeout_markdown,
)


def test_deterministic_same_result_twice():
    a = build_readonly_final_closeout_markdown()
    b = build_readonly_final_closeout_markdown()
    assert a == b


def test_contains_no_live_trading():
    md = build_readonly_final_closeout_markdown()
    lower = md.lower()
    assert "no live trading" in lower or "no live authorization" in lower


def test_contains_frozen_boundaries():
    md = build_readonly_final_closeout_markdown()
    for boundary in [
        "no live trading",
        "no real execution",
        "no secret access",
        "no network call",
        "no planner integration",
    ]:
        assert boundary in md.lower(), f"missing frozen boundary: {boundary}"


def test_contains_task_range():
    md = build_readonly_final_closeout_markdown()
    assert "T826-T853" in md


def test_non_empty():
    md = build_readonly_final_closeout_markdown()
    assert len(md) > 0
