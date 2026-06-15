from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from core.risk_manager import RiskManager


@pytest.fixture
def mock_config():
    return {
        "balance": 1000.0,
        "risk": {
            "starting_balance_usdt": 1000.0,
            "risk_per_trade": 0.02,
            "max_daily_loss_pct": 0.06,
            "max_consecutive_losses": 3,
            "cooldown_minutes": 20,
            "min_notional_usdt": 25.0,
            "max_notional_usdt": 250.0,
            "leverage": 3,
        },
    }


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("ok", (True, "ok")),
        ("cooldown_active", (False, "cooldown_active")),
        ("daily_loss_limit", (False, "daily_loss_limit")),
        ("consecutive_loss_limit", (False, "consecutive_loss_limit")),
        ("balance_depleted", (False, "balance_depleted")),
    ],
)
def test_can_open_new_trade(mock_config, mock_logger, case, expected):
    manager = RiskManager(mock_config, mock_logger)
    timestamp = datetime(2026, 4, 18, 12, 0, tzinfo=timezone.utc)
    manager._current_day = timestamp.date()
    symbol = "BTCUSDT"

    if case == "cooldown_active":
        manager._symbol_state[symbol] = {
            "consecutive_losses": 0,
            "cooldown_until": timestamp + timedelta(minutes=1),
        }
    elif case == "daily_loss_limit":
        manager.daily_pnl = -(manager.starting_balance * manager.max_daily_loss_pct)
    elif case == "consecutive_loss_limit":
        manager._symbol_state[symbol] = {
            "consecutive_losses": manager.max_consecutive_losses,
            "cooldown_until": None,
        }
    elif case == "balance_depleted":
        manager.balance = 0.0

    assert manager.can_open_new_trade(symbol, timestamp) == expected


@pytest.mark.parametrize(
    ("signal", "symbol", "open_positions", "expected"),
    [
        (
            {"entry": 100.0, "stop": 90.0, "tp": 120.0},
            "BTCUSDT",
            0,
            {
                "quantity": 2.0,
                "risk_amount": 20.0,
                "estimated_loss_at_stop": 20.0,
                "estimated_gain_at_target": 40.0,
                "reward_risk_ratio": 2.0,
                "notional": 200.0,
                "leverage": 3,
                "symbol": "BTCUSDT",
            },
        ),
        (
            {"entry": 100.0, "stop": 200.0, "tp": 50.0},
            "ETHUSDT",
            0,
            {
                "quantity": 0.25,
                "risk_amount": 20.0,
                "estimated_loss_at_stop": 25.0,
                "estimated_gain_at_target": 12.5,
                "reward_risk_ratio": 0.5,
                "notional": 25.0,
                "leverage": 3,
                "symbol": "ETHUSDT",
            },
        ),
        (
            {"entry": 100.0, "stop": 99.0, "tp": 95.0},
            "SOLUSDT",
            0,
            {
                "quantity": 2.5,
                "risk_amount": 20.0,
                "estimated_loss_at_stop": 2.5,
                "estimated_gain_at_target": 12.5,
                "reward_risk_ratio": 5.0,
                "notional": 250.0,
                "leverage": 3,
                "symbol": "SOLUSDT",
            },
        ),
        (
            {"entry": 100.0, "stop": 100.0, "tp": 110.0},
            "XRPUSDT",
            0,
            {
                "quantity": 0.0,
                "risk_amount": 0.0,
                "estimated_loss_at_stop": 0.0,
                "estimated_gain_at_target": 0.0,
                "reward_risk_ratio": 0.0,
                "notional": 0.0,
                "symbol": "XRPUSDT",
            },
        ),
    ],
)
def test_calculate_position(mock_config, mock_logger, signal, symbol, open_positions, expected):
    manager = RiskManager(mock_config, mock_logger)

    position = manager.calculate_position(signal, symbol, open_positions)

    assert position["entry_price"] == pytest.approx(signal["entry"])
    assert position["stop_price"] == pytest.approx(signal["stop"])
    assert position["take_profit_price"] == pytest.approx(signal["tp"])
    assert position["quantity"] == pytest.approx(expected["quantity"])
    assert position["risk_amount"] == pytest.approx(expected["risk_amount"])
    assert position["estimated_loss_at_stop"] == pytest.approx(
        expected["estimated_loss_at_stop"]
    )
    assert position["estimated_gain_at_target"] == pytest.approx(
        expected["estimated_gain_at_target"]
    )
    assert position["reward_risk_ratio"] == pytest.approx(expected["reward_risk_ratio"])
    assert position["notional"] == pytest.approx(expected["notional"])
    assert position["symbol"] == expected["symbol"]

    if expected["quantity"] > 0:
        assert position["leverage"] == expected["leverage"]
    else:
        assert "leverage" not in position


class TestOnTradeClosed:
    def test_updates_balance(self, mock_config, mock_logger):
        manager = RiskManager(mock_config, mock_logger)
        assert manager.balance == 1000.0
        manager.on_trade_closed({"symbol": "BTCUSDT", "pnl": 10.0, "exit_time": datetime(2026, 4, 18, 12, 0, tzinfo=timezone.utc)})
        assert manager.balance == 1010.0

    def test_updates_daily_pnl(self, mock_config, mock_logger):
        manager = RiskManager(mock_config, mock_logger)
        manager.on_trade_closed({"symbol": "BTCUSDT", "pnl": -5.0, "exit_time": datetime(2026, 4, 18, 12, 0, tzinfo=timezone.utc)})
        assert manager.daily_pnl == -5.0

    def test_increments_consecutive_losses(self, mock_config, mock_logger):
        manager = RiskManager(mock_config, mock_logger)
        ts = datetime(2026, 4, 18, 12, 0, tzinfo=timezone.utc)
        manager.on_trade_closed({"symbol": "BTCUSDT", "pnl": -1.0, "exit_time": ts})
        assert manager._symbol_state["BTCUSDT"]["consecutive_losses"] == 1
        manager.on_trade_closed({"symbol": "BTCUSDT", "pnl": -1.0, "exit_time": ts})
        assert manager._symbol_state["BTCUSDT"]["consecutive_losses"] == 2

    def test_resets_consecutive_losses_on_win(self, mock_config, mock_logger):
        manager = RiskManager(mock_config, mock_logger)
        ts = datetime(2026, 4, 18, 12, 0, tzinfo=timezone.utc)
        manager._symbol_state["BTCUSDT"] = {"consecutive_losses": 2, "cooldown_until": None}
        manager.on_trade_closed({"symbol": "BTCUSDT", "pnl": 5.0, "exit_time": ts})
        assert manager._symbol_state["BTCUSDT"]["consecutive_losses"] == 0

    def test_sets_cooldown(self, mock_config, mock_logger):
        manager = RiskManager(mock_config, mock_logger)
        ts = datetime(2026, 4, 18, 12, 0, tzinfo=timezone.utc)
        manager.on_trade_closed({"symbol": "BTCUSDT", "pnl": -1.0, "exit_time": ts})
        cooldown = manager._symbol_state["BTCUSDT"]["cooldown_until"]
        assert cooldown is not None
        assert cooldown == ts + timedelta(minutes=20)


class TestMarginCheck:
    def test_margin_limits_quantity(self, mock_config, mock_logger):
        config = {
            "balance": 100.0,
            "risk": {
                "starting_balance_usdt": 100.0,
                "risk_per_trade": 0.02,
                "max_daily_loss_pct": 0.06,
                "max_consecutive_losses": 3,
                "cooldown_minutes": 20,
                "min_notional_usdt": 10.0,
                "max_notional_usdt": 10000.0,
                "leverage": 1,
            },
        }
        manager = RiskManager(config, mock_logger)
        signal = {"entry": 100.0, "stop": 110.0, "tp": 90.0}
        position = manager.calculate_position(signal, "BTCUSDT", 0)
        assert position["quantity"] * 100.0 / 1.0 <= 100.0 * 0.95

    def test_margin_limits_quantity_with_leverage(self, mock_config, mock_logger):
        config = {
            "balance": 50.0,
            "risk": {
                "starting_balance_usdt": 50.0,
                "risk_per_trade": 0.02,
                "max_daily_loss_pct": 0.06,
                "max_consecutive_losses": 3,
                "cooldown_minutes": 20,
                "min_notional_usdt": 10.0,
                "max_notional_usdt": 10000.0,
                "leverage": 10,
            },
        }
        manager = RiskManager(config, mock_logger)
        signal = {"entry": 100.0, "stop": 101.0, "tp": 98.0}
        position = manager.calculate_position(signal, "BTCUSDT", 0)
        margin = position["notional"] / 10.0
        assert margin <= 50.0 * 0.95 + 0.01
