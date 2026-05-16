from __future__ import annotations

from scripts.testnet_state_snapshot_common import (
    classify_protection_state,
    normalize_symbol_state,
    summarize_state_snapshot,
)


def test_classify_fully_protected() -> None:
    row = {"symbol": "BTCUSDT", "positionAmt": 1.0, "openAlgoOrdersCount": 2, "protection_status": "FULLY_PROTECTED", "ok": True}
    norm = normalize_symbol_state(row)
    assert norm is not None
    assert classify_protection_state(norm) == "FULLY_PROTECTED"


def test_classify_orphan_protection() -> None:
    row = {"symbol": "ETHUSDT", "positionAmt": 0.0, "openAlgoOrdersCount": 1, "ok": True}
    norm = normalize_symbol_state(row)
    assert norm is not None
    assert classify_protection_state(norm) == "ORPHAN_PROTECTION"


def test_classify_naked_position() -> None:
    row = {"symbol": "SOLUSDT", "positionAmt": 2.0, "openAlgoOrdersCount": 0, "ok": False}
    norm = normalize_symbol_state(row)
    assert norm is not None
    assert classify_protection_state(norm) == "NAKED_POSITION"


def test_missing_or_invalid_row() -> None:
    assert normalize_symbol_state({}) is None
    assert normalize_symbol_state({"symbol": "", "positionAmt": 1}) is None


def test_aggregate_summary_counts() -> None:
    rows = [
        {"symbol": "BTCUSDT", "positionAmt": 1, "openAlgoOrdersCount": 2, "protection_status": "FULLY_PROTECTED", "ok": True},
        {"symbol": "ETHUSDT", "positionAmt": 0, "openAlgoOrdersCount": 1, "ok": True},
        {"symbol": "SOLUSDT", "positionAmt": 1, "openAlgoOrdersCount": 0, "ok": False},
        {"symbol": "XRPUSDT", "positionAmt": 0, "openAlgoOrdersCount": 0, "ok": True},
    ]
    summary = summarize_state_snapshot(rows)
    assert summary["total"] == 4
    assert summary["ok_count"] == 3
    assert summary["error_count"] == 1
    assert summary["counts"]["FULLY_PROTECTED"] == 1
    assert summary["counts"]["ORPHAN_PROTECTION"] == 1
    assert summary["counts"]["NAKED_POSITION"] == 1
    assert summary["counts"]["FLAT_CLEAN"] == 1
