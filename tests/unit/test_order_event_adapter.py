from core.order_event_adapter import adapt_broker_order_update
from core.order_state import (
    ORDER_EVENT_ACCEPTED,
    ORDER_EVENT_CANCELED,
    ORDER_EVENT_FILLED,
    ORDER_EVENT_PARTIALLY_FILLED,
    ORDER_EVENT_REJECTED,
    ORDER_STATUS_ACCEPTED,
    ORDER_STATUS_CANCELED,
    ORDER_STATUS_FILLED,
    ORDER_STATUS_PARTIALLY_FILLED,
    ORDER_STATUS_REJECTED,
)


def test_adapt_broker_order_update_maps_supported_statuses():
    mapping = [
        ("NEW", ORDER_EVENT_ACCEPTED, ORDER_STATUS_ACCEPTED),
        ("PARTIALLY_FILLED", ORDER_EVENT_PARTIALLY_FILLED, ORDER_STATUS_PARTIALLY_FILLED),
        ("FILLED", ORDER_EVENT_FILLED, ORDER_STATUS_FILLED),
        ("CANCELED", ORDER_EVENT_CANCELED, ORDER_STATUS_CANCELED),
        ("REJECTED", ORDER_EVENT_REJECTED, ORDER_STATUS_REJECTED),
    ]

    for external_status, expected_event, expected_status in mapping:
        adapted = adapt_broker_order_update(
            {
                "order_id": "B-1",
                "trade_id": 7,
                "symbol": "BTCUSDT",
                "side": "SHORT",
                "status": external_status,
                "qty": 2.0,
                "filled_qty": 1.0,
                "avg_fill_price": 100.5,
            }
        )

        assert adapted["ok"] is True
        assert adapted["event"]["event_type"] == expected_event
        assert adapted["event"]["status"] == expected_status
        assert adapted["event"]["order_id"] == "B-1"
        assert adapted["event"]["symbol"] == "BTCUSDT"


def test_adapt_broker_order_update_handles_unknown_status_safely():
    adapted = adapt_broker_order_update(
        {
            "order_id": "B-2",
            "status": "UNEXPECTED",
            "symbol": "ETHUSDT",
            "side": "SHORT",
        }
    )

    assert adapted["ok"] is False
    assert adapted["reason"] == "unknown_external_status"
    assert adapted["event"]["event_type"] == ORDER_EVENT_REJECTED
    assert "unknown_external_status" in adapted["event"]["reason"]
