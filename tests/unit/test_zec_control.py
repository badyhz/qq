from __future__ import annotations

import json
import stat

import pytest

from core.zec_4h_live import LiveAction, StrategyDecision, StrategyState, save_strategy_state
from scripts.run_zec_4h_small_live import _load_runtime_state, _risk_increase_block_reason

from core.zec_control import (
    ControlConflictError,
    RuntimeConfig,
    UnsafeConfigurationChange,
    append_audit,
    assert_safe_configuration_change,
    load_runtime_config,
    update_runtime_config,
    validate_exchange_symbol,
    write_runtime_config,
)


def test_runtime_config_is_fail_closed_and_atomic_0600(tmp_path):
    path = tmp_path / "control" / "runtime_config.json"
    config = load_runtime_config(path, create=True)
    assert config.strategy_enabled is False
    assert config.revision == 1
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert not list(path.parent.glob("*.tmp"))


def test_migration_can_preserve_an_already_armed_strategy(tmp_path):
    path = tmp_path / "control" / "runtime_config.json"
    config = load_runtime_config(path, create=True, initial_strategy_enabled=True)
    assert config.strategy_enabled is True
    assert load_runtime_config(path).strategy_enabled is True


def test_runtime_config_rejects_cap_leverage_and_unknown_strategy(tmp_path):
    path = tmp_path / "runtime_config.json"
    with pytest.raises(ValueError, match="capital_cap_usdt"):
        write_runtime_config(path, RuntimeConfig(capital_cap_usdt=51))
    with pytest.raises(ValueError, match="leverage"):
        write_runtime_config(path, RuntimeConfig(leverage=20))
    with pytest.raises(ValueError, match="strategy_id"):
        write_runtime_config(path, RuntimeConfig(strategy_id="invented"))
    with pytest.raises(ValueError, match="timeframe"):
        write_runtime_config(path, RuntimeConfig(timeframe="3h"))
    with pytest.raises(ValueError, match="sizing_base_usdt"):
        write_runtime_config(path, RuntimeConfig(sizing_base_usdt=0))
    with pytest.raises(ValueError, match="sizing_base_usdt"):
        write_runtime_config(path, RuntimeConfig(sizing_base_usdt=51))


def test_revision_conflict_does_not_overwrite(tmp_path):
    path = tmp_path / "runtime_config.json"
    audit = tmp_path / "audit.jsonl"
    first = load_runtime_config(path, create=True)
    second = update_runtime_config(
        path,
        expected_revision=first.revision,
        changes={"strategy_enabled": True},
        audit_path=audit,
    )
    with pytest.raises(ControlConflictError):
        update_runtime_config(
            path,
            expected_revision=first.revision,
            changes={"strategy_enabled": False},
            audit_path=audit,
        )
    assert load_runtime_config(path).revision == second.revision
    assert load_runtime_config(path).strategy_enabled is True


def test_audit_is_append_only_0600_and_redacts_secret_named_fields(tmp_path):
    path = tmp_path / "audit.jsonl"
    append_audit(path, {"event": "ONE", "password": "never-write-this"})
    append_audit(path, {"event": "TWO", "api_secret": "never-write-this"})
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [row["event"] for row in rows] == ["ONE", "TWO"]
    assert "never-write-this" not in path.read_text()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_exchange_symbol_must_be_trading_usdt_perpetual():
    config = RuntimeConfig(symbol="BTCUSDT")
    item = validate_exchange_symbol(config, {"symbols": [{
        "symbol": "BTCUSDT",
        "status": "TRADING",
        "quoteAsset": "USDT",
        "contractType": "PERPETUAL",
    }]})
    assert item["symbol"] == "BTCUSDT"
    with pytest.raises(ValueError, match="not trading"):
        validate_exchange_symbol(config, {"symbols": [{
            "symbol": "BTCUSDT", "status": "BREAK", "quoteAsset": "USDT",
            "contractType": "PERPETUAL",
        }]})


def test_identity_change_requires_flat_quiescent_engine():
    before = RuntimeConfig()
    after = RuntimeConfig(symbol="BTCUSDT", revision=2)
    assert_safe_configuration_change(
        before, after, position_qty=0, open_order_count=0, pending_action="", recovery_status=""
    )
    with pytest.raises(UnsafeConfigurationChange, match="POSITION_OPEN"):
        assert_safe_configuration_change(
            before, after, position_qty=0.01, open_order_count=0, pending_action="", recovery_status=""
        )
    with pytest.raises(UnsafeConfigurationChange, match="OPEN_ORDERS"):
        assert_safe_configuration_change(
            before, after, position_qty=0, open_order_count=1, pending_action="", recovery_status=""
        )
    with pytest.raises(UnsafeConfigurationChange, match="PENDING_ACTION"):
        assert_safe_configuration_change(
            before, after, position_qty=0, open_order_count=0, pending_action="OPEN", recovery_status=""
        )
    with pytest.raises(UnsafeConfigurationChange, match="RECOVERY_ACTIVE"):
        assert_safe_configuration_change(
            before, after, position_qty=0, open_order_count=0, pending_action="", recovery_status="RECOVERING"
        )


def test_control_update_rejects_unknown_and_immutable_fields(tmp_path):
    path = tmp_path / "runtime_config.json"
    audit = tmp_path / "audit.jsonl"
    current = load_runtime_config(path, create=True)
    with pytest.raises(ValueError, match="governed"):
        update_runtime_config(path, expected_revision=current.revision, changes={"leverage": 100}, audit_path=audit)
    with pytest.raises(ValueError, match="unknown"):
        update_runtime_config(path, expected_revision=current.revision, changes={"manual_order": True}, audit_path=audit)


def _decision(action: str, close_time: str = "2026-09-01T04:00:00+00:00") -> StrategyDecision:
    return StrategyDecision(
        action=action,
        signal_key=f"key:{action}",
        client_order_id=f"id:{action}",
        bar_close_time=close_time,
        signal_price=100,
        entry_low=90,
        reason="TEST",
    )


def test_strategy_off_blocks_only_risk_increase():
    config = RuntimeConfig(strategy_enabled=False)
    assert _risk_increase_block_reason(_decision(LiveAction.OPEN.value), config) == "STRATEGY_DISABLED_RISK_INCREASE_BLOCKED"
    assert _risk_increase_block_reason(_decision(LiveAction.ADD_50.value), config) == "STRATEGY_DISABLED_RISK_INCREASE_BLOCKED"
    assert _risk_increase_block_reason(_decision(LiveAction.STOP_CLOSE.value), config) == ""
    assert _risk_increase_block_reason(_decision(LiveAction.TAKE_PROFIT_CLOSE.value), config) == ""
    assert _risk_increase_block_reason(_decision(LiveAction.HARD_STOP_CLOSE.value), config) == ""


def test_reenable_boundary_blocks_old_risk_increase_only():
    config = RuntimeConfig(
        strategy_enabled=True,
        risk_increase_after_bar_close_time="2026-09-01T04:00:00+00:00",
    )
    assert _risk_increase_block_reason(_decision(LiveAction.OPEN.value), config) == "PRE_ENABLE_BAR_RISK_INCREASE_BLOCKED"
    assert _risk_increase_block_reason(
        _decision(LiveAction.OPEN.value, "2026-09-01T08:00:00+00:00"), config
    ) == ""
    assert _risk_increase_block_reason(_decision(LiveAction.STOP_CLOSE.value), config) == ""


def test_config_revision_change_archives_old_state_and_starts_cold(tmp_path):
    state_path = tmp_path / "runtime" / "state.json"
    old = StrategyState(warmup_complete=True, last_signal="BUY", config_revision=1)
    save_strategy_state(state_path, old)
    new = _load_runtime_state(
        state_path,
        RuntimeConfig(revision=2, strategy_enabled=False, symbol="BTCUSDT"),
    )
    assert new.symbol == "BTCUSDT"
    assert new.config_revision == 2
    assert new.warmup_complete is False
    archives = list((state_path.parent / "archive").glob("state.zec_4h_live_v1.ZECUSDT.4h.rev1.*.json"))
    assert len(archives) == 1
    assert json.loads(archives[0].read_text())["last_signal"] == "BUY"


def test_toggle_only_revision_preserves_position_and_indicator_state(tmp_path):
    state_path = tmp_path / "runtime" / "state.json"
    old = StrategyState(
        config_revision=1,
        warmup_complete=True,
        last_signal="BUY",
        actual_position_qty=0.25,
        full_position_qty=0.25,
    )
    save_strategy_state(state_path, old)
    migrated = _load_runtime_state(
        state_path,
        RuntimeConfig(revision=2, strategy_enabled=False),
    )
    assert migrated.config_revision == 2
    assert migrated.warmup_complete is True
    assert migrated.last_signal == "BUY"
    assert migrated.actual_position_qty == 0.25
    assert not (state_path.parent / "archive").exists()
