from core.reconciliation import build_state_consistency_report


def test_reconciliation_reports_consistent_open_state():
    report = build_state_consistency_report(
        has_position=True,
        position={
            "symbol": "BTCUSDT",
            "quantity": 1.5,
            "margin_required": 100.0,
            "total_fees": 0.25,
        },
    )

    assert report["is_consistent"] is True
    assert report["violations"] == []


def test_reconciliation_reports_consistent_closed_trade_state():
    report = build_state_consistency_report(
        has_position=False,
        position=None,
        closed_trade={
            "trade_id": 1,
            "symbol": "BTCUSDT",
            "side": "SHORT",
            "entry_price": 100.0,
            "exit_price": 95.0,
            "quantity": 2.0,
            "gross_pnl": 10.0,
            "total_fees": 0.5,
            "fees_paid": 0.5,
            "net_pnl": 9.5,
            "entry_time": "2026-04-19T10:00:00+00:00",
            "exit_time": "2026-04-19T10:05:00+00:00",
            "duration_sec": 300,
            "exit_reason": "TAKE_PROFIT",
        },
    )

    assert report["is_consistent"] is True
    assert report["violations"] == []


def test_reconciliation_detects_residual_position_after_close():
    report = build_state_consistency_report(
        has_position=False,
        position={
            "symbol": "BTCUSDT",
            "quantity": 1.0,
            "margin_required": 10.0,
            "total_fees": 0.1,
        },
    )

    assert report["is_consistent"] is False
    assert "has_position_false_but_position_present" in report["violations"]


def test_reconciliation_detects_negative_margin_and_fees():
    report = build_state_consistency_report(
        has_position=True,
        position={
            "symbol": "BTCUSDT",
            "quantity": 1.0,
            "margin_required": -1.0,
            "total_fees": -0.2,
        },
        closed_trade={
            "trade_id": 2,
            "symbol": "BTCUSDT",
            "side": "SHORT",
            "entry_price": 100.0,
            "exit_price": 110.0,
            "quantity": 1.0,
            "gross_pnl": -10.0,
            "net_pnl": -11.0,
            "total_fees": -1.0,
            "fees_paid": -1.0,
            "entry_time": "2026-04-19T10:00:00+00:00",
            "exit_time": "2026-04-19T10:10:00+00:00",
            "duration_sec": 600,
            "exit_reason": "STOP_LOSS",
            "margin_required": -1.0,
        },
    )

    assert report["is_consistent"] is False
    assert "margin_required_negative" in report["violations"]
    assert "total_fees_negative" in report["violations"]
    assert "closed_trade_margin_required_negative" in report["violations"]
    assert "closed_trade_total_fees_negative" in report["violations"]


def test_reconciliation_handles_missing_closed_trade_fields_without_crashing():
    report = build_state_consistency_report(
        has_position=False,
        position=None,
        closed_trade={"trade_id": 3, "symbol": "BTCUSDT"},
    )

    assert report["is_consistent"] is False
    assert any(v.startswith("missing_closed_trade_fields:") for v in report["violations"])
