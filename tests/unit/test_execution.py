from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from core.execution import ExecutionEngine


@pytest.fixture
def mock_config():
    return {
        "mode": "dry-run",
        "strategy_profile": "mean_reversion",
        "execution": {
            "dry_run_fee_rate": 0.0004,
            "slippage_threshold": 0.003,
            "allow_live_without_protection": False,
        },
    }


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def mock_order_manager():
    return MagicMock()


@pytest.fixture
def mock_exchange():
    return MagicMock()


def test_dry_run_open_short_success(
    mock_config, mock_logger, mock_order_manager, mock_exchange
):
    timestamp = datetime.now(timezone.utc).isoformat()
    position_plan = {
        "quantity": 2.5,
        "stop_price": 105.0,
        "take_profit_price": 90.0,
        "reward_risk_ratio": 2.0,
        "estimated_loss_at_stop": 12.5,
        "estimated_gain_at_target": 25.0,
    }
    signal = {
        "symbol": "BTCUSDT",
        "score": 0.91,
        "reasons": ["zscore_extreme", "volume_confirmation"],
        "meta": {
            "zscore": 2.4,
            "strategy_profile": "intraday_mean_reversion",
        },
    }
    market = {
        "close": 100.0,
        "timestamp": timestamp,
    }

    engine = ExecutionEngine(mock_config, mock_order_manager, mock_exchange, mock_logger)

    result = engine.open_short(position_plan, signal, market)
    expected_reference_entry_price = 100.0
    expected_entry_fill_price = expected_reference_entry_price
    expected_entry_fee = expected_entry_fill_price * position_plan["quantity"] * mock_config["execution"]["dry_run_fee_rate"]
    expected_notional = position_plan["quantity"] * expected_entry_fill_price
    expected_leverage = 1.0
    expected_margin_required = expected_notional / expected_leverage

    assert result["accepted"] is True
    assert result["mode"] == "dry-run"
    assert result["symbol"] == signal["symbol"]
    assert result["entry_price"] == pytest.approx(expected_entry_fill_price)
    assert result["stop_price"] == pytest.approx(105.0)
    assert result["take_profit_price"] == pytest.approx(90.0)
    assert result["quantity"] == pytest.approx(2.5)
    assert result["notional"] == pytest.approx(expected_notional)
    assert result["fees_paid"] == pytest.approx(expected_entry_fee)
    assert result["fee_rate"] == pytest.approx(mock_config["execution"]["dry_run_fee_rate"])
    assert result["reference_entry_price"] == pytest.approx(expected_reference_entry_price)
    assert result["entry_fill_price"] == pytest.approx(expected_entry_fill_price)
    assert result["entry_fee"] == pytest.approx(expected_entry_fee)
    assert result["total_fees"] == pytest.approx(expected_entry_fee)
    assert result["leverage"] == pytest.approx(expected_leverage)
    assert result["margin_required"] == pytest.approx(expected_margin_required)
    assert result["entry_price"] == pytest.approx(result["entry_fill_price"])
    assert result["fees_paid"] == pytest.approx(result["entry_fee"])
    assert result["total_fees"] == pytest.approx(result["fees_paid"])
    assert result["meta"] == {
        "signal_reasons": signal["reasons"],
        "reward_risk_ratio": position_plan["reward_risk_ratio"],
        "estimated_loss_at_stop": position_plan["estimated_loss_at_stop"],
        "estimated_gain_at_target": position_plan["estimated_gain_at_target"],
        "strategy_profile": signal["meta"]["strategy_profile"],
    }
    assert result["notes"] == "dry_run_open"
    assert result["execution_duration"] >= 0.0
    mock_exchange.is_enabled.assert_not_called()
    mock_exchange.place_short_bracket.assert_not_called()


@pytest.mark.parametrize("quantity", [0.0, -0.5])
def test_open_short_invalid_quantity_rejected(
    mock_config, mock_logger, mock_order_manager, mock_exchange, quantity
):
    timestamp = datetime.now(timezone.utc).isoformat()
    position_plan = {
        "quantity": quantity,
        "stop_price": 105.0,
        "take_profit_price": 90.0,
    }
    signal = {
        "symbol": "BTCUSDT",
        "score": 0.4,
        "meta": {"zscore": 1.1},
    }
    market = {
        "close": 100.0,
        "timestamp": timestamp,
    }

    engine = ExecutionEngine(mock_config, mock_order_manager, mock_exchange, mock_logger)

    result = engine.open_short(position_plan, signal, market)

    assert result == {"accepted": False, "reason": "invalid_quantity"}
    mock_logger.warning.assert_called_once_with(
        "Execution rejected | reason=invalid_quantity | quantity=%s",
        quantity,
    )
    mock_exchange.is_enabled.assert_not_called()
    mock_exchange.place_short_bracket.assert_not_called()
