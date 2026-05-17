from __future__ import annotations

from scripts.check_testnet_state_common import (
    build_testnet_state_result,
    classify_testnet_protection_status,
    normalize_open_algo_orders,
    normalize_position_risk_row,
)


def test_no_position_classified_flat_clean() -> None:
    pos = normalize_position_risk_row({"symbol": "BTCUSDT", "positionAmt": "0", "entryPrice": "0", "markPrice": "0"})
    algo = normalize_open_algo_orders([])
    status = classify_testnet_protection_status(pos, algo)
    assert status["protection_status"] == "FLAT_CLEAN"


def test_fully_protected() -> None:
    pos = normalize_position_risk_row({"symbol": "BTCUSDT", "positionAmt": "1", "entryPrice": "100", "markPrice": "101"})
    algo = normalize_open_algo_orders([
        {"type": "STOP_MARKET"},
        {"type": "TAKE_PROFIT_MARKET"},
    ])
    status = classify_testnet_protection_status(pos, algo)
    assert status["protection_status"] == "FULLY_PROTECTED"


def test_orphan_protection() -> None:
    pos = normalize_position_risk_row({"symbol": "BTCUSDT", "positionAmt": "0"})
    algo = normalize_open_algo_orders([{"type": "STOP_MARKET"}])
    status = classify_testnet_protection_status(pos, algo)
    assert status["protection_status"] == "ORPHAN_PROTECTION"


def test_naked_position() -> None:
    pos = normalize_position_risk_row({"symbol": "BTCUSDT", "positionAmt": "2"})
    algo = normalize_open_algo_orders([])
    status = classify_testnet_protection_status(pos, algo)
    assert status["protection_status"] == "NAKED_POSITION"


def test_partial_protection_and_result_builder() -> None:
    pos = normalize_position_risk_row({"symbol": "ethusdt", "positionAmt": "-1.5", "entryPrice": "2000", "markPrice": "1990"})
    algo = normalize_open_algo_orders([{"origType": "STOP_MARKET"}])
    status = classify_testnet_protection_status(pos, algo)
    assert status["protection_status"] == "PARTIAL_PROTECTED"

    result = build_testnet_state_result("ethusdt", pos, algo, metadata={"env": "testnet"})
    assert result["symbol"] == "ETHUSDT"
    assert result["env"] == "testnet"
    assert result["openAlgoOrdersCount"] == 1
    assert result["protection_status"] == "PARTIAL_PROTECTED"
