"""Test sandbox adapter contract."""
import pytest
from src.runtime_integrations.testnet_sandbox.adapter_contract import validate_contract_implementation, SandboxAdapterContract
from src.runtime_integrations.testnet_sandbox.simulated_exchange_adapter import SimulatedExchangeAdapter
from src.runtime_integrations.testnet_sandbox.sandbox_types import ConnectionConfig, OrderIntent


def test_adapter_implements_contract():
    valid, missing = validate_contract_implementation(SimulatedExchangeAdapter)
    assert valid
    assert len(missing) == 0


def test_adapter_is_subclass():
    assert issubclass(SimulatedExchangeAdapter, SandboxAdapterContract)


def test_validate_connection_config_rejects_real_keys():
    adapter = SimulatedExchangeAdapter()
    config = ConnectionConfig("real_key_here", "real_secret", "https://testnet.binance.vision", True)
    result = adapter.validate_connection_config(config)
    assert not result.valid


def test_validate_connection_config_accepts_placeholder():
    adapter = SimulatedExchangeAdapter()
    config = ConnectionConfig("PLACEHOLDER_KEY_REPLACE_ME", "PLACEHOLDER_SECRET", "https://testnet.binance.vision", True)
    result = adapter.validate_connection_config(config)
    assert result.valid


def test_validate_connection_config_requires_testnet():
    adapter = SimulatedExchangeAdapter()
    config = ConnectionConfig("PLACEHOLDER", "PLACEHOLDER", "https://testnet.binance.vision", False)
    result = adapter.validate_connection_config(config)
    assert not result.valid


def test_build_order_intent():
    adapter = SimulatedExchangeAdapter()
    intent = adapter.build_order_intent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "SIG_001")
    assert intent.symbol == "BTCUSDT"
    assert intent.side == "BUY"
    assert intent.quantity == 0.001


def test_validate_order_intent_valid():
    adapter = SimulatedExchangeAdapter()
    intent = OrderIntent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "LIMIT", "SIG_001")
    result = adapter.validate_order_intent(intent)
    assert result.valid


def test_validate_order_intent_rejects_bad_side():
    adapter = SimulatedExchangeAdapter()
    intent = OrderIntent("BTCUSDT", "HOLD", "LIMIT", 0.001, 50000.0, "LIMIT", "SIG_001")
    result = adapter.validate_order_intent(intent)
    assert not result.valid


def test_validate_order_intent_rejects_zero_quantity():
    adapter = SimulatedExchangeAdapter()
    intent = OrderIntent("BTCUSDT", "BUY", "LIMIT", 0.0, 50000.0, "LIMIT", "SIG_001")
    result = adapter.validate_order_intent(intent)
    assert not result.valid


def test_simulate_submit_returns_simulated():
    adapter = SimulatedExchangeAdapter()
    intent = OrderIntent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "LIMIT", "SIG_001")
    result = adapter.simulate_submit(intent)
    assert result.simulated is True
    assert result.real_submit is False
    assert result.testnet_submit is False
    assert result.no_submit_enforced is True
    assert result.status == "SIMULATED_NEW"


def test_simulate_cancel():
    adapter = SimulatedExchangeAdapter()
    intent = OrderIntent("BTCUSDT", "BUY", "LIMIT", 0.001, 50000.0, "LIMIT", "SIG_001")
    submit = adapter.simulate_submit(intent)
    cancel = adapter.simulate_cancel(submit.order_id, "BTCUSDT")
    assert cancel.simulated is True
    assert cancel.status == "SIMULATED_CANCELLED"


def test_simulate_cancel_not_found():
    adapter = SimulatedExchangeAdapter()
    cancel = adapter.simulate_cancel("FAKE_ID", "BTCUSDT")
    assert cancel.status == "SIMULATED_NOT_FOUND"


def test_get_simulated_balance():
    adapter = SimulatedExchangeAdapter()
    bal = adapter.get_simulated_balance("USDT")
    assert bal.simulated is True
    assert bal.free == 10000.0


def test_get_simulated_balance_unknown():
    adapter = SimulatedExchangeAdapter()
    bal = adapter.get_simulated_balance("FAKECOIN")
    assert bal.simulated is True
    assert bal.total == 0.0


def test_get_simulated_positions_empty():
    adapter = SimulatedExchangeAdapter()
    positions = adapter.get_simulated_positions()
    assert len(positions) == 0
