import pytest

from core.order_events import apply_order_event, initialize_order
from core.order_state import (
    ORDER_EVENT_ACCEPTED,
    ORDER_EVENT_FILLED,
    ORDER_EVENT_PARTIALLY_FILLED,
    ORDER_STATUS_FILLED,
    ORDER_STATUS_PARTIALLY_FILLED,
)


def test_order_events_partial_fill_progress_and_weighted_average():
    order, _ = initialize_order(
        order_id="evt-1",
        trade_id=1,
        symbol="BTCUSDT",
        side="SHORT",
        qty=3.0,
    )
    accepted = apply_order_event(order, event_type=ORDER_EVENT_ACCEPTED)
    assert accepted["ok"] is True
    order = accepted["order"]

    p1 = apply_order_event(
        order,
        event_type=ORDER_EVENT_PARTIALLY_FILLED,
        filled_qty=1.0,
        remaining_qty=2.0,
        avg_fill_price=100.0,
    )
    assert p1["ok"] is True
    assert p1["order"]["status"] == ORDER_STATUS_PARTIALLY_FILLED
    assert p1["order"]["avg_fill_price"] == pytest.approx(100.0)

    p2 = apply_order_event(
        p1["order"],
        event_type=ORDER_EVENT_PARTIALLY_FILLED,
        filled_qty=2.0,
        remaining_qty=1.0,
        avg_fill_price=110.0,
    )
    assert p2["ok"] is True
    assert p2["order"]["filled_qty"] == pytest.approx(2.0)
    assert p2["order"]["remaining_qty"] == pytest.approx(1.0)
    assert p2["order"]["avg_fill_price"] == pytest.approx(105.0)

    p3 = apply_order_event(
        p2["order"],
        event_type=ORDER_EVENT_PARTIALLY_FILLED,
        filled_qty=3.0,
        remaining_qty=0.0,
        avg_fill_price=120.0,
    )
    assert p3["ok"] is True
    assert p3["order"]["status"] == ORDER_STATUS_FILLED
    assert p3["order"]["filled_qty"] == pytest.approx(3.0)
    assert p3["order"]["remaining_qty"] == pytest.approx(0.0)
    assert p3["order"]["avg_fill_price"] == pytest.approx(110.0)


def test_order_events_reject_overfill():
    order, _ = initialize_order(
        order_id="evt-2",
        trade_id=1,
        symbol="BTCUSDT",
        side="SHORT",
        qty=2.0,
    )
    accepted = apply_order_event(order, event_type=ORDER_EVENT_ACCEPTED)
    assert accepted["ok"] is True

    overfill = apply_order_event(
        accepted["order"],
        event_type=ORDER_EVENT_PARTIALLY_FILLED,
        filled_qty=2.1,
        remaining_qty=0.0,
        avg_fill_price=100.0,
    )
    assert overfill["ok"] is False
    assert overfill["reason"] == "overfill"


def test_order_events_reject_partial_after_filled():
    order, _ = initialize_order(
        order_id="evt-3",
        trade_id=1,
        symbol="BTCUSDT",
        side="SHORT",
        qty=1.0,
    )
    accepted = apply_order_event(order, event_type=ORDER_EVENT_ACCEPTED)
    filled = apply_order_event(
        accepted["order"],
        event_type=ORDER_EVENT_FILLED,
        filled_qty=1.0,
        remaining_qty=0.0,
        avg_fill_price=100.0,
    )
    assert filled["ok"] is True

    invalid = apply_order_event(
        filled["order"],
        event_type=ORDER_EVENT_PARTIALLY_FILLED,
        filled_qty=1.0,
        remaining_qty=0.0,
        avg_fill_price=100.0,
    )
    assert invalid["ok"] is False
    assert invalid["reason"] == "invalid_state_transition"
