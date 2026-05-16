from __future__ import annotations

from scripts.testnet_state_snapshot_report_common import (
    build_snapshot_archive_payload,
    render_snapshot_markdown,
    summarize_snapshot_rows,
)


def test_summarize_snapshot_rows_normal_protected() -> None:
    rows = [
        {
            "ok": True,
            "symbol": "btcusdt",
            "positionAmt": 1.0,
            "entryPrice": 100.0,
            "markPrice": 101.0,
            "openAlgoOrdersCount": 2,
            "open_stop_market_count": 1,
            "open_take_profit_market_count": 1,
            "protection_status": "fully_protected",
            "action_required": "",
        }
    ]
    summary = summarize_snapshot_rows(rows)
    assert summary["ok"] is True
    assert summary["aggregate_status"] == "CLEAN"
    assert summary["status_counts"]["FULLY_PROTECTED"] == 1
    assert summary["fully_protected_symbols"] == ["BTCUSDT"]


def test_summarize_snapshot_rows_risk_status_counts() -> None:
    rows = [
        {"ok": True, "symbol": "A", "protection_status": "ORPHAN_PROTECTION"},
        {"ok": True, "symbol": "B", "protection_status": "NAKED_POSITION"},
        {"ok": True, "symbol": "C", "protection_status": "PARTIAL_PROTECTED"},
        {"ok": True, "symbol": "D", "protection_status": "FLAT_CLEAN"},
    ]
    summary = summarize_snapshot_rows(rows)
    assert summary["aggregate_status"] == "CRITICAL"
    assert summary["status_counts"]["ORPHAN_PROTECTION"] == 1
    assert summary["status_counts"]["NAKED_POSITION"] == 1
    assert summary["status_counts"]["PARTIAL_PROTECTED"] == 1
    assert summary["status_counts"]["FLAT_CLEAN"] == 1
    assert set(summary["risky_symbols"]) == {"A", "B", "C"}


def test_render_snapshot_markdown_contains_summary_sections() -> None:
    summary = {
        "snapshot_id": "snapshot_1",
        "env": "testnet",
        "ts_utc": "2026-05-17T00:00:00Z",
        "aggregate_status": "WARNING",
        "symbols": ["A", "B"],
        "per_symbol_state": [
            {"symbol": "A", "positionAmt": 0, "entryPrice": 0, "markPrice": 0, "openAlgoOrdersCount": 1, "open_stop_market_count": 0, "open_take_profit_market_count": 1, "protection_status": "ORPHAN_PROTECTION", "action_required": "", "ok": True}
        ],
        "status_counts": {
            "FULLY_PROTECTED": 0,
            "ORPHAN_PROTECTION": 1,
            "PARTIAL_PROTECTED": 0,
            "NAKED_POSITION": 0,
            "FLAT_CLEAN": 0,
            "UNKNOWN": 0,
        },
        "risky_symbols": ["A"],
        "clean_symbols": [],
        "fully_protected_symbols": [],
    }
    md = render_snapshot_markdown(summary)
    assert "# Testnet State Snapshot" in md
    assert "## Summary" in md
    assert "## Per Symbol State" in md
    assert "## Status Counts" in md
    assert "aggregate_status: WARNING" in md


def test_build_snapshot_archive_payload_includes_metadata_rows_summary() -> None:
    rows = [
        {"ok": True, "symbol": "A", "protection_status": "FLAT_CLEAN"},
        {"ok": False, "symbol": "B", "protection_status": "UNKNOWN"},
    ]
    metadata = {"snapshot_id": "x1", "env": "testnet", "ts_utc": "t", "symbols": ["A", "B"]}
    payload = build_snapshot_archive_payload(rows, metadata)
    assert payload["snapshot_id"] == "x1"
    assert payload["env"] == "testnet"
    assert payload["symbols"] == ["A", "B"]
    assert len(payload["per_symbol_state"]) == 2
    assert "status_counts" in payload
    assert payload["ok"] is False
