"""Unit tests for Phase 10C-3J Feishu-ready paper alert payloads."""
from __future__ import annotations

from core.paper_trading.feishu_paper_alert_payload import build_payloads_from_preview, render_markdown


def _preview() -> dict:
    return {
        "date": "2026-06-18",
        "mode": "real_public_http",
        "plans": [
            {
                "symbol": "BNBUSDT",
                "timeframe": "5m",
                "direction": "LONG_OBSERVE",
                "source_status": "TRIGGERED",
                "entry_observation": 590.68,
                "invalidation_level": 589.49,
                "take_profit_observation": 593.06,
                "rr_ratio": 2.0,
                "risk_distance_pct": 0.2,
                "reward_distance_pct": 0.4,
                "plan_decision": "WATCH",
                "reason": "long triggered",
            },
            {
                "symbol": "XRPUSDT",
                "timeframe": "15m",
                "direction": "SHORT_OBSERVE",
                "source_status": "SHORT_TRIGGERED",
                "entry_observation": 1.1662,
                "invalidation_level": 1.16,
                "take_profit_observation": 0.0,
                "rr_ratio": 0.0,
                "risk_distance_pct": 0.53,
                "reward_distance_pct": 0.0,
                "plan_decision": "WAIT",
                "reason": "mixed timeframe",
            },
        ],
    }


def test_builds_watch_only_payloads() -> None:
    result = build_payloads_from_preview(_preview())
    assert result["payload_count"] == 1
    assert result["decision_counts"] == {"WATCH": 1, "WAIT": 1, "AVOID": 0}
    assert result["payload_scope"] == "WATCH_ONLY"
    assert result["payloads"][0]["symbol"] == "BNBUSDT"


def test_payload_is_dry_run_and_not_sent() -> None:
    payload = build_payloads_from_preview(_preview())["payloads"][0]
    assert payload["dry_run_only"] is True
    assert payload["actually_sent"] is False
    assert payload["webhook_send_attempted"] is False
    assert payload["not_order_payload"] is True
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in payload["final_verdict"]


def test_feishu_card_shape() -> None:
    payload = build_payloads_from_preview(_preview())["payloads"][0]
    card = payload["feishu_payload"]
    assert card["msg_type"] == "interactive"
    assert card["card"]["header"]["template"] == "orange"
    assert "BNBUSDT" in card["card"]["header"]["title"]["content"]
    assert "No webhook sent" in card["card"]["elements"][-1]["elements"][0]["content"]


def test_wait_plans_are_skipped_not_alerted() -> None:
    result = build_payloads_from_preview(_preview())
    assert result["skipped"]["WAIT"][0]["symbol"] == "XRPUSDT"
    assert all(p["symbol"] != "XRPUSDT" for p in result["payloads"])


def test_markdown_contains_safety_and_preview() -> None:
    result = build_payloads_from_preview(_preview())
    md = render_markdown(result)
    assert "Phase 10C-3J" in md
    assert "[PAPER WATCH] BNBUSDT 5m LONG_OBSERVE" in md
    assert "No webhook send attempted" in md
    assert "Not a trading recommendation" in md
