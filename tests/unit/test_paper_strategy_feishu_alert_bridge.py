"""Tests for strategy Feishu alert bridge — payload generation, safety, Chinese labels."""
from __future__ import annotations

import os
import py_compile

import pytest

from core.paper_trading.strategy_feishu_alert_bridge import (
    build_strategy_payloads,
    render_strategy_markdown,
    _build_one_payload,
    _message_text,
    StrategyFeishuPayload,
    WATCH_STATE_CN,
    PRIORITY_CN,
)


MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "..",
                           "core", "paper_trading", "strategy_feishu_alert_bridge.py")


def _make_plan(**overrides):
    plan = {
        "symbol": "BNBUSDT",
        "timeframe": "15m",
        "direction": "LONG_OBSERVE",
        "source_status": "NEAR_TURN_UP",
        "last_close": 600.0,
        "entry_observation": 600.0,
        "invalidation_level": 590.0,
        "take_profit_observation": 620.0,
        "rr_ratio": 2.0,
        "risk_distance_pct": 1.67,
        "reward_distance_pct": 3.33,
        "plan_decision": "WATCH",
        "reason": "macd_rebound_watch: BULLISH_CROSS, NEAR_TURN_UP",
    }
    plan.update(overrides)
    return plan


def _make_payload_input(**overrides):
    data = {
        "date": "2026-06-18",
        "mode": "real_public_http",
        "plans": [_make_plan()],
        "decision_counts": {"WATCH": 1, "WAIT": 0, "AVOID": 0},
    }
    data.update(overrides)
    return data


class TestModuleCompiles:
    def test_compiles(self):
        py_compile.compile(MODULE_PATH, doraise=True)


class TestBuildStrategyPayloads:
    def test_basic_structure(self):
        result = build_strategy_payloads(_make_payload_input())
        assert result["date"] == "2026-06-18"
        assert result["payload_count"] == 1
        assert result["payload_scope"] == "WATCH_ONLY"
        assert result["dry_run_only"] is True
        assert result["actually_sent"] is False
        assert result["webhook_send_attempted"] is False
        assert result["not_order_payload"] is True

    def test_safety_flags_present(self):
        result = build_strategy_payloads(_make_payload_input())
        flags = result["safety_flags"]
        for required in ["PAPER_ONLY", "NO_ORDER", "NO_REAL_ORDER", "NO_SECRET"]:
            assert required in flags

    def test_empty_plans(self):
        result = build_strategy_payloads(_make_payload_input(plans=[]))
        assert result["payload_count"] == 0
        assert result["payloads"] == []

    def test_only_watch_plans(self):
        plans = [
            _make_plan(plan_decision="WATCH"),
            _make_plan(plan_decision="WAIT", symbol="ETHUSDT"),
            _make_plan(plan_decision="AVOID", symbol="SOLUSDT"),
        ]
        result = build_strategy_payloads(_make_payload_input(plans=plans))
        assert result["payload_count"] == 1

    def test_multiple_watch_plans(self):
        plans = [
            _make_plan(plan_decision="WATCH"),
            _make_plan(plan_decision="WATCH", symbol="ETHUSDT"),
        ]
        result = build_strategy_payloads(_make_payload_input(plans=plans))
        assert result["payload_count"] == 2

    def test_decision_counts_preserved(self):
        counts = {"WATCH": 3, "WAIT": 2, "AVOID": 1}
        result = build_strategy_payloads(_make_payload_input(decision_counts=counts))
        assert result["decision_counts"] == counts

    def test_payload_has_strategy_id(self):
        result = build_strategy_payloads(_make_payload_input())
        payload = result["payloads"][0]
        assert payload["strategy_id"] == "macd_rebound_watch"

    def test_payload_has_title_format(self):
        result = build_strategy_payloads(_make_payload_input())
        payload = result["payloads"][0]
        assert payload["title"].startswith("[PAPER STRATEGY]")
        assert "BNBUSDT" in payload["title"]
        assert "15m" in payload["title"]
        assert "多头观察" in payload["title"]

    def test_payload_has_chinese_message(self):
        result = build_strategy_payloads(_make_payload_input())
        payload = result["payloads"][0]
        msg = payload["message_text"]
        assert "策略：macd_rebound_watch" in msg
        assert "标的：BNBUSDT" in msg
        assert "方向：多头观察" in msg
        assert "观察价：" in msg
        assert "失效价：" in msg
        assert "安全边界：" in msg

    def test_feishu_card_structure(self):
        result = build_strategy_payloads(_make_payload_input())
        payload = result["payloads"][0]
        card = payload["feishu_payload"]
        assert card["msg_type"] == "interactive"
        assert "card" in card
        assert card["card"]["header"]["template"] == "orange"


class TestBuildOnePayload:
    def test_short_observe_direction(self):
        plan = _make_plan(direction="SHORT_OBSERVE", source_status="SHORT_WATCH",
                          reason="weak_short_watch: HIST_EXPANDING_RED, SHORT_WATCH")
        payload = _build_one_payload(plan)
        assert payload.direction == "SHORT_OBSERVE"
        assert "空头观察" in payload.title
        assert payload.strategy_id == "weak_short_watch"

    def test_dry_run_flags(self):
        payload = _build_one_payload(_make_plan())
        assert payload.dry_run_only is True
        assert payload.actually_sent is False
        assert payload.webhook_send_attempted is False
        assert payload.not_order_payload is True

    def test_dedup_key_deterministic(self):
        plan = _make_plan()
        p1 = _build_one_payload(plan)
        p2 = _build_one_payload(plan)
        assert p1.dedup_key == p2.dedup_key

    def test_different_plans_different_dedup(self):
        p1 = _build_one_payload(_make_plan())
        p2 = _build_one_payload(_make_plan(symbol="ETHUSDT"))
        assert p1.dedup_key != p2.dedup_key


class TestMessageText:
    def test_has_all_fields(self):
        plan = _make_plan()
        msg = _message_text(plan, "macd_rebound_watch")
        for field in ["策略：", "标的：", "周期：", "方向：", "优先级：", "触发状态：",
                       "观察价：", "失效价：", "目标观察：", "R:R：", "风险距离：", "目标空间：",
                       "处理建议：", "安全边界："]:
            assert field in msg, f"missing field: {field}"

    def test_chinese_timeframe(self):
        plan = _make_plan(timeframe="1h")
        msg = _message_text(plan, "test")
        assert "1小时" in msg

    def test_chinese_watch_state(self):
        plan = _make_plan(source_status="NEAR_TURN_UP")
        msg = _message_text(plan, "test")
        assert "即将转折向上" in msg


class TestRenderMarkdown:
    def test_has_title(self):
        result = build_strategy_payloads(_make_payload_input())
        md = render_strategy_markdown(result)
        assert "策略信号飞书预览" in md

    def test_has_safety_section(self):
        result = build_strategy_payloads(_make_payload_input())
        md = render_strategy_markdown(result)
        assert "安全边界" in md
        assert "不下单" in md

    def test_empty_payloads(self):
        result = build_strategy_payloads(_make_payload_input(plans=[]))
        md = render_strategy_markdown(result)
        assert "暂无信号提醒" in md

    def test_has_decision_table(self):
        result = build_strategy_payloads(_make_payload_input())
        md = render_strategy_markdown(result)
        assert "| WATCH |" in md


class TestNoForbiddenPatterns:
    def test_no_order_words(self):
        with open(MODULE_PATH) as f:
            content = f.read()
        for word in ["submit_order", "place_order", "cancel_order", "execute_trade"]:
            assert word not in content, f"forbidden word: {word}"

    def test_no_env_reads(self):
        with open(MODULE_PATH) as f:
            content = f.read()
        assert "os.environ" not in content
        assert "os.getenv" not in content

    def test_no_webhook_url(self):
        with open(MODULE_PATH) as f:
            content = f.read()
        assert "--webhook-url" not in content
        assert "--allow-send" not in content

    def test_no_websocket_imports(self):
        import ast
        with open(MODULE_PATH) as f:
            tree = ast.parse(f.read())
        forbidden = {"websocket", "aiohttp"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden
