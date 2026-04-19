from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from core.order_manager import OrderManager


@pytest.fixture
def mock_config():
    return {
        "mode": "dry-run",
        "strategy_profile": "mean_reversion",
        "execution": {
            "dry_run_slippage_rate": 0.001,
        },
    }


@pytest.fixture
def mock_execution_result():
    quantity = 2.5
    reference_entry_price = 100.0
    entry_fill_price = 99.9
    fee_rate = 0.0004
    entry_fee = entry_fill_price * quantity * fee_rate
    notional = entry_fill_price * quantity
    return {
        "accepted": True,
        "mode": "dry-run",
        "symbol": "BTCUSDT",
        "reference_entry_price": reference_entry_price,
        "entry_fill_price": entry_fill_price,
        "entry_price": entry_fill_price,
        "stop_price": 105.0,
        "take_profit_price": 90.0,
        "quantity": quantity,
        "notional": notional,
        "entry_fee": entry_fee,
        "total_fees": entry_fee,
        "fees_paid": entry_fee,
        "fee_rate": fee_rate,
        "leverage": 1.0,
        "margin_required": notional,
        "meta": {
            "strategy_profile": "intraday_mean_reversion",
            "reward_risk_ratio": 2.0,
            "estimated_loss_at_stop": 12.5,
            "estimated_gain_at_target": 25.0,
        },
        "notes": "dry_run_open",
    }


@pytest.fixture
def mock_signal():
    mock_meta_source = MagicMock()
    return {
        "symbol": "BTCUSDT",
        "score": 2,
        "meta": {
            "strategy_profile": "intraday_mean_reversion",
            "reward_risk_ratio": 2.0,
            "zscore": 2.4,
            "vwap": 99.5,
            "vwap_dev": 0.8,
            "atr": 3.2,
            "volume_ratio": 1.7,
            "source": mock_meta_source,
        },
    }


@pytest.fixture
def mock_market():
    return {
        "close": 100.0,
        "high": 101.0,
        "low": 99.0,
        "timestamp": datetime(2026, 4, 18, 12, 0, tzinfo=timezone.utc),
    }


def test_has_position_returns_false_initially(mock_config):
    manager = OrderManager(mock_config)

    assert manager.has_position() is False


def test_can_open_returns_true_initially(mock_config):
    manager = OrderManager(mock_config)

    assert manager.can_open() is True


def test_open_position_updates_state_and_stores_fields(
    mock_config, mock_execution_result, mock_signal, mock_market
):
    manager = OrderManager(mock_config)

    manager.open_position(mock_execution_result, mock_signal, mock_market)

    assert manager.has_position() is True
    assert manager.can_open() is False

    position = manager.current_position()
    assert position is not None
    assert position["trade_id"] == 1
    assert position["mode"] == mock_execution_result["mode"]
    assert position["symbol"] == mock_execution_result["symbol"]
    assert position["side"] == "SHORT"
    assert position["entry_price"] == pytest.approx(mock_execution_result["entry_price"])
    assert position["reference_entry_price"] == pytest.approx(
        mock_execution_result["reference_entry_price"]
    )
    assert position["entry_fill_price"] == pytest.approx(
        mock_execution_result["entry_fill_price"]
    )
    assert position["stop_price"] == pytest.approx(mock_execution_result["stop_price"])
    assert position["take_profit_price"] == pytest.approx(
        mock_execution_result["take_profit_price"]
    )
    assert position["quantity"] == pytest.approx(mock_execution_result["quantity"])
    assert position["notional"] == pytest.approx(mock_execution_result["notional"])
    assert position["entry_fee"] == pytest.approx(mock_execution_result["entry_fee"])
    assert position["total_fees"] == pytest.approx(mock_execution_result["total_fees"])
    assert position["fees_paid"] == pytest.approx(mock_execution_result["fees_paid"])
    assert position["fee_rate"] == pytest.approx(mock_execution_result["fee_rate"])
    assert position["leverage"] == pytest.approx(mock_execution_result["leverage"])
    assert position["margin_required"] == pytest.approx(
        mock_execution_result["margin_required"]
    )
    assert position["opened_at"] == mock_market["timestamp"]
    assert position["score"] == mock_signal["score"]
    assert position["strategy_profile"] == mock_signal["meta"]["strategy_profile"]
    assert position["signal_meta"] == mock_signal["meta"]
    assert position["execution_meta"] == mock_execution_result["meta"]
    assert position["reward_risk_ratio"] == pytest.approx(
        mock_execution_result["meta"]["reward_risk_ratio"]
    )
    assert position["estimated_loss_at_stop"] == pytest.approx(
        mock_execution_result["meta"]["estimated_loss_at_stop"]
    )
    assert position["estimated_gain_at_target"] == pytest.approx(
        mock_execution_result["meta"]["estimated_gain_at_target"]
    )
    assert position["highest_price_seen"] == pytest.approx(
        mock_execution_result["entry_price"]
    )
    assert position["lowest_price_seen"] == pytest.approx(
        mock_execution_result["entry_price"]
    )
    assert position["notes"] == mock_execution_result["notes"]


@pytest.mark.parametrize(
    ("market_overrides", "expected_exit_price", "expected_reason", "expected_gross_pnl"),
    [
        (
            {"high": 105.0, "low": 95.0},
            105.0,
            "STOP_LOSS",
            -12.5,
        ),
        (
            {"high": 103.0, "low": 90.0},
            90.0,
            "TAKE_PROFIT",
            25.0,
        ),
    ],
)
def test_update_market_triggers_close(
    mock_config,
    mock_execution_result,
    mock_signal,
    mock_market,
    market_overrides,
    expected_exit_price,
    expected_reason,
    expected_gross_pnl,
):
    manager = OrderManager(mock_config)
    manager.open_position(mock_execution_result, mock_signal, mock_market)

    close_time = mock_market["timestamp"] + timedelta(minutes=5)
    market = {
        **mock_market,
        **market_overrides,
        "timestamp": close_time,
    }

    closed_trade = manager.update_market(market)

    assert closed_trade is not None
    assert closed_trade["trade_id"] == 1
    assert closed_trade["symbol"] == mock_execution_result["symbol"]
    assert closed_trade["mode"] == mock_execution_result["mode"]
    assert closed_trade["side"] == "SHORT"
    assert closed_trade["entry_price"] == pytest.approx(mock_execution_result["entry_price"])
    assert closed_trade["reference_entry_price"] == pytest.approx(
        mock_execution_result["reference_entry_price"]
    )
    assert closed_trade["entry_fill_price"] == pytest.approx(
        mock_execution_result["entry_fill_price"]
    )
    assert closed_trade["stop_price"] == pytest.approx(mock_execution_result["stop_price"])
    assert closed_trade["take_profit_price"] == pytest.approx(
        mock_execution_result["take_profit_price"]
    )
    assert closed_trade["quantity"] == pytest.approx(mock_execution_result["quantity"])
    assert closed_trade["notional"] == pytest.approx(mock_execution_result["notional"])
    assert closed_trade["margin_required"] == pytest.approx(
        mock_execution_result["margin_required"]
    )

    expected_exit_fill_price = expected_exit_price * (
        1.0 + mock_config["execution"]["dry_run_slippage_rate"]
    )
    expected_reference_gross_pnl = expected_gross_pnl
    expected_gross_pnl = (
        mock_execution_result["entry_fill_price"] - expected_exit_fill_price
    ) * mock_execution_result["quantity"]
    expected_exit_fee = (
        expected_exit_fill_price
        * mock_execution_result["quantity"]
        * mock_execution_result["fee_rate"]
    )
    expected_total_fees = mock_execution_result["entry_fee"] + expected_exit_fee
    expected_slippage_cost = expected_reference_gross_pnl - expected_gross_pnl
    expected_net_pnl = expected_gross_pnl - expected_total_fees
    expected_return_pct = expected_net_pnl / mock_execution_result["notional"] * 100.0

    assert closed_trade["reference_exit_price"] == pytest.approx(expected_exit_price)
    assert closed_trade["exit_fill_price"] == pytest.approx(expected_exit_fill_price)
    assert closed_trade["exit_fee"] == pytest.approx(expected_exit_fee)
    assert closed_trade["total_fees"] == pytest.approx(expected_total_fees)
    assert closed_trade["reference_gross_pnl"] == pytest.approx(
        expected_reference_gross_pnl
    )
    assert closed_trade["gross_pnl"] == pytest.approx(expected_gross_pnl)
    assert closed_trade["slippage_cost"] == pytest.approx(expected_slippage_cost)
    assert closed_trade["net_pnl"] == pytest.approx(expected_net_pnl)
    assert closed_trade["exit_price"] == pytest.approx(expected_exit_fill_price)
    assert closed_trade["fees_paid"] == pytest.approx(expected_total_fees)
    assert closed_trade["pnl"] == pytest.approx(expected_net_pnl)
    assert closed_trade["return_pct"] == pytest.approx(expected_return_pct)
    assert closed_trade["score"] == mock_signal["score"]
    assert closed_trade["strategy_profile"] == mock_signal["meta"]["strategy_profile"]
    assert closed_trade["zscore"] == pytest.approx(mock_signal["meta"]["zscore"])
    assert closed_trade["vwap"] == pytest.approx(mock_signal["meta"]["vwap"])
    assert closed_trade["vwap_dev"] == pytest.approx(mock_signal["meta"]["vwap_dev"])
    assert closed_trade["atr"] == pytest.approx(mock_signal["meta"]["atr"])
    assert closed_trade["volume_ratio"] == pytest.approx(mock_signal["meta"]["volume_ratio"])
    assert closed_trade["reward_risk_ratio"] == pytest.approx(
        mock_execution_result["meta"]["reward_risk_ratio"]
    )
    assert closed_trade["estimated_loss_at_stop"] == pytest.approx(
        mock_execution_result["meta"]["estimated_loss_at_stop"]
    )
    assert closed_trade["estimated_gain_at_target"] == pytest.approx(
        mock_execution_result["meta"]["estimated_gain_at_target"]
    )
    assert closed_trade["entry_time"] == mock_market["timestamp"]
    assert closed_trade["exit_time"] == close_time
    assert closed_trade["duration_sec"] == pytest.approx(300.0)
    assert closed_trade["exit_reason"] == expected_reason
    assert closed_trade["notes"] == mock_execution_result["notes"]
    assert manager.has_position() is False
    assert manager.current_position() is None


def test_update_market_with_no_trigger_returns_none(
    mock_config, mock_execution_result, mock_signal, mock_market
):
    manager = OrderManager(mock_config)
    manager.open_position(mock_execution_result, mock_signal, mock_market)

    market = {
        **mock_market,
        "high": 104.9,
        "low": 90.1,
        "timestamp": mock_market["timestamp"] + timedelta(minutes=5),
    }

    result = manager.update_market(market)

    assert result is None
    assert manager.has_position() is True
    assert manager.can_open() is False
