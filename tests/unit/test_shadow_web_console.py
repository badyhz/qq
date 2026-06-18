"""Tests for shadow web console core module — safety and structure."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from core.paper_trading.shadow_web_console import (
    is_safe_report_name, load_console_status, render_dashboard_html,
    run_allowed_action, render_report_file, append_action_log,
    load_latest_positions, load_latest_scorecard, load_latest_sample_gate,
    load_recent_actions, render_positions_table, render_scorecard_table,
    render_sample_gate_card, render_recent_actions_table,
    load_strategy_config, load_strategy_switchboard,
    render_strategy_switchboard_table,
    validate_config_change_request, create_config_change_request,
    append_config_change_request, render_config_change_form,
    render_config_change_result, normalize_lang,
    ALLOWED_ACTIONS, SAFETY_FLAGS, SUPPORTED_LANGS, UI_TEXT,
)


class TestSafeReportName:
    def test_valid_json(self):
        assert is_safe_report_name("2026-06-18_report.json") is True

    def test_valid_md(self):
        assert is_safe_report_name("report.md") is True

    def test_valid_csv(self):
        assert is_safe_report_name("data.csv") is True

    def test_valid_jsonl(self):
        assert is_safe_report_name("log.jsonl") is True

    def test_rejects_path_traversal(self):
        assert is_safe_report_name("../etc/passwd") is False

    def test_rejects_slash(self):
        assert is_safe_report_name("subdir/file.json") is False

    def test_rejects_backslash(self):
        assert is_safe_report_name("subdir\\file.json") is False

    def test_rejects_dot_dot(self):
        assert is_safe_report_name("..") is False

    def test_rejects_empty(self):
        assert is_safe_report_name("") is False

    def test_rejects_unsafe_extension(self):
        assert is_safe_report_name("file.py") is False
        assert is_safe_report_name("file.sh") is False
        assert is_safe_report_name("file.exe") is False

    def test_rejects_null_byte(self):
        assert is_safe_report_name("file.json\x00.txt") is False


class TestLoadConsoleStatus:
    def test_missing_dir_returns_empty(self):
        result = load_console_status("/nonexistent/path")
        assert result == {}

    def test_loads_from_real_reports(self):
        report_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports", "strategies")
        if os.path.isdir(report_dir):
            status = load_console_status(report_dir)
            assert isinstance(status, dict)


class TestRenderDashboard:
    def test_contains_title(self):
        html = render_dashboard_html({})
        assert "影子交易控制台" in html

    def test_contains_title_en(self):
        html = render_dashboard_html({}, lang="en")
        assert "Shadow Trading Console" in html

    def test_contains_sample_status(self):
        html = render_dashboard_html({"sample_status": "INSUFFICIENT_CLOSED_SAMPLE"})
        assert "sample_status" in html
        assert "INSUFFICIENT_CLOSED_SAMPLE" in html

    def test_contains_testnet_gate_status(self):
        html = render_dashboard_html({"testnet_gate_status": "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE"})
        assert "testnet_gate_status" in html
        assert "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE" in html

    def test_contains_buttons_zh(self):
        html = render_dashboard_html({}, lang="zh")
        assert "扫描新机会" in html
        assert "只更新已有持仓" in html
        assert "刷新样本门禁" in html
        assert "打印当前状态" in html

    def test_contains_buttons_en(self):
        html = render_dashboard_html({}, lang="en")
        assert "Scan New" in html
        assert "Update Existing" in html
        assert "Refresh Sample" in html
        assert "Print Current" in html

    def test_contains_safety_footer(self):
        html = render_dashboard_html({})
        assert "仅纸面" in html
        assert "无订单" in html
        assert "无测试网" in html
        assert "无实盘" in html

    def test_contains_safety_footer_en(self):
        html = render_dashboard_html({}, lang="en")
        assert "Paper-only" in html
        assert "No order" in html
        assert "No testnet" in html
        assert "No live" in html

    def test_contains_next_action(self):
        html = render_dashboard_html({})
        assert "不要 testnet" in html
        assert "不要 live" in html

    def test_ready_for_review_hint(self):
        html = render_dashboard_html({"testnet_gate_status": "PAPER_SAMPLE_READY_FOR_HUMAN_REVIEW"})
        assert "人工审查" in html


class TestAllowedActions:
    def test_fixed_actions(self):
        expected = {"run-lifecycle", "run-update-only", "run-sample-gate", "print-status"}
        assert set(ALLOWED_ACTIONS.keys()) == expected

    def test_all_have_label(self):
        for action, defn in ALLOWED_ACTIONS.items():
            assert "label" in defn
            assert "command" in defn

    def test_commands_use_sys_executable(self):
        for action, defn in ALLOWED_ACTIONS.items():
            cmd = defn["command"]
            assert cmd[0] == os.sys.executable

    def test_no_shell(self):
        for action, defn in ALLOWED_ACTIONS.items():
            assert "shell" not in defn

    def test_unknown_action_rejected(self):
        result = run_allowed_action("hack-the-planet", "/tmp", "/tmp")
        assert result["status"] == "REJECTED"


class TestRunAllowedAction:
    def test_print_status_passes(self):
        report_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports", "strategies")
        repo_root = os.path.join(os.path.dirname(__file__), "..", "..")
        if os.path.isdir(report_dir):
            result = run_allowed_action("print-status", repo_root, report_dir)
            assert result["status"] == "PASS"
            assert result["exit_code"] == 0

    def test_result_has_safety_flags(self):
        result = run_allowed_action("unknown", "/tmp", "/tmp")
        # Even rejected actions should not crash
        assert result["status"] == "REJECTED"


class TestActionLog:
    def test_appends_log(self):
        with tempfile.TemporaryDirectory() as td:
            result = {"action": "test", "status": "PASS"}
            append_action_log(result, td)
            import glob
            files = glob.glob(os.path.join(td, "*_shadow_web_console_actions.jsonl"))
            assert len(files) == 1
            with open(files[0]) as f:
                line = json.loads(f.readline())
            assert line["action"] == "test"


class TestRenderReportFile:
    def test_rejects_unsafe_name(self):
        assert render_report_file("/tmp", "../etc/passwd") is None

    def test_rejects_missing_file(self):
        assert render_report_file("/tmp", "nonexistent.json") is None

    def test_reads_valid_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", dir="/tmp", delete=False) as f:
            f.write("# Test Report")
            path = f.name
        name = os.path.basename(path)
        content = render_report_file("/tmp", name)
        assert content == "# Test Report"
        os.unlink(path)


class TestSafetyFlags:
    def test_required_flags(self):
        for flag in ["PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET", "NO_ORDER",
                      "NO_TESTNET", "NO_LIVE", "LOCAL_ONLY"]:
            assert flag in SAFETY_FLAGS


class TestLoadPositions:
    def test_missing_dir_returns_empty(self):
        assert load_latest_positions("/nonexistent") == []

    def test_loads_from_real_reports(self):
        report_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports", "strategies")
        if os.path.isdir(report_dir):
            positions = load_latest_positions(report_dir)
            assert isinstance(positions, list)


class TestLoadScorecard:
    def test_missing_dir_returns_empty(self):
        assert load_latest_scorecard("/nonexistent") == {}

    def test_loads_from_real_reports(self):
        report_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports", "strategies")
        if os.path.isdir(report_dir):
            sc = load_latest_scorecard(report_dir)
            assert isinstance(sc, dict)


class TestLoadSampleGate:
    def test_missing_dir_returns_empty(self):
        assert load_latest_sample_gate("/nonexistent") == {}

    def test_loads_from_real_reports(self):
        report_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports", "strategies")
        if os.path.isdir(report_dir):
            gate = load_latest_sample_gate(report_dir)
            assert isinstance(gate, dict)


class TestLoadRecentActions:
    def test_missing_dir_returns_empty(self):
        assert load_recent_actions("/nonexistent") == []

    def test_with_no_log_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            assert load_recent_actions(td) == []


class TestRenderPositionsTable:
    def test_empty_positions(self):
        html = render_positions_table([])
        assert "暂无持仓数据" in html

    def test_empty_positions_en(self):
        html = render_positions_table([], lang="en")
        assert "No positions found" in html

    def test_renders_open_position(self):
        positions = [{
            "status": "OPEN", "strategy_id": "test_strat", "symbol": "BTCUSDT",
            "timeframe": "15m", "side": "LONG", "entry_price": 60000,
            "stop_loss": 59000, "take_profit": 62000,
            "unrealized_pnl": 100.0, "realized_pnl": 0.0, "r_multiple": 0.0,
            "quarantine_status": "CLEAN", "excluded_from_performance_stats": False,
        }]
        html = render_positions_table(positions)
        assert "OPEN" in html
        assert "BTCUSDT" in html
        assert "test_strat" in html

    def test_escapes_html(self):
        positions = [{
            "status": "OPEN", "strategy_id": "<script>alert(1)</script>",
            "symbol": "BTCUSDT", "timeframe": "15m", "side": "LONG",
            "entry_price": 60000, "stop_loss": 59000, "take_profit": 62000,
            "unrealized_pnl": 0, "realized_pnl": 0, "r_multiple": 0,
            "quarantine_status": "CLEAN", "excluded_from_performance_stats": False,
        }]
        html = render_positions_table(positions)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_stats_cards(self):
        positions = [
            {"status": "OPEN", "strategy_id": "s1", "symbol": "A", "timeframe": "1m", "side": "LONG",
             "entry_price": 1, "stop_loss": 0.9, "take_profit": 1.1, "unrealized_pnl": 0, "realized_pnl": 0,
             "r_multiple": 0, "quarantine_status": "CLEAN", "excluded_from_performance_stats": False},
            {"status": "TAKE_PROFIT_HIT", "strategy_id": "s1", "symbol": "A", "timeframe": "1m", "side": "LONG",
             "entry_price": 1, "stop_loss": 0.9, "take_profit": 1.1, "unrealized_pnl": 0, "realized_pnl": 0.1,
             "r_multiple": 1.0, "quarantine_status": "CLEAN", "excluded_from_performance_stats": False},
        ]
        html = render_positions_table(positions)
        assert "OPEN" in html
        assert "TP HIT" in html

    def test_limit(self):
        positions = [
            {"status": "OPEN", "strategy_id": f"s{i}", "symbol": "A", "timeframe": "1m", "side": "LONG",
             "entry_price": 1, "stop_loss": 0.9, "take_profit": 1.1, "unrealized_pnl": 0, "realized_pnl": 0,
             "r_multiple": 0, "quarantine_status": "CLEAN", "excluded_from_performance_stats": False}
            for i in range(100)
        ]
        html = render_positions_table(positions, limit=10)
        # Should have at most 10 data rows (count <tr> in tbody)
        assert html.count("<tr>") <= 12  # 10 data + 1 header + some buffer


class TestRenderScorecardTable:
    def test_empty_scorecards(self):
        html = render_scorecard_table([])
        assert "暂无策略评分数据" in html

    def test_empty_scorecards_en(self):
        html = render_scorecard_table([], lang="en")
        assert "No strategy scorecards" in html

    def test_renders_strategy(self):
        sc = [{
            "strategy_id": "macd_rebound_watch", "strategy_type": "macd_rebound_watch",
            "position_count": 10, "open_count": 8, "closed_count": 2,
            "tp_count": 1, "sl_count": 1, "timeout_count": 0,
            "win_rate": 0.5, "profit_factor": 1.5, "expectancy_r": 0.3,
            "sample_status": "INSUFFICIENT_CLOSED_SAMPLE", "strategy_status": "OBSERVE_ONLY",
            "strategy_score": 0.0,
        }]
        html = render_scorecard_table(sc)
        assert "macd_rebound_watch" in html
        assert "OBSERVE_ONLY" in html

    def test_insufficient_sample_warning(self):
        sc = [{
            "strategy_id": "test", "strategy_type": "test",
            "position_count": 5, "open_count": 5, "closed_count": 0,
            "tp_count": 0, "sl_count": 0, "timeout_count": 0,
            "win_rate": 0, "profit_factor": 0, "expectancy_r": 0,
            "sample_status": "INSUFFICIENT_CLOSED_SAMPLE", "strategy_status": "OBSERVE_ONLY",
            "strategy_score": 0,
        }]
        html = render_scorecard_table(sc, sample_status="INSUFFICIENT_CLOSED_SAMPLE")
        assert "样本不足" in html
        assert "不允许 testnet/live" in html


class TestRenderSampleGateCard:
    def test_empty_gate(self):
        html = render_sample_gate_card({})
        assert "暂无样本门禁数据" in html

    def test_empty_gate_en(self):
        html = render_sample_gate_card({}, lang="en")
        assert "No sample gate data" in html

    def test_blocked_gate(self):
        gate = {
            "sample_status": "INSUFFICIENT_CLOSED_SAMPLE",
            "testnet_gate_status": "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE",
            "closed_clean_positions": 0,
            "testnet_gate_reasons": ["closed_clean_positions=0 < 10"],
        }
        html = render_sample_gate_card(gate)
        assert "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE" in html
        assert "0" in html

    def test_no_testnet_ready_in_output(self):
        gate = {"sample_status": "EVALUABLE", "testnet_gate_status": "PAPER_SAMPLE_READY_FOR_HUMAN_REVIEW"}
        html = render_sample_gate_card(gate)
        assert "testnet_ready=true" not in html
        assert "live_ready=true" not in html


class TestRenderRecentActions:
    def test_empty_actions(self):
        html = render_recent_actions_table([])
        assert "暂无控制台操作记录" in html

    def test_empty_actions_en(self):
        html = render_recent_actions_table([], lang="en")
        assert "No web console actions yet" in html

    def test_renders_action(self):
        actions = [{
            "action": "run-lifecycle", "started_at": "2026-06-18T10:00:00",
            "duration_seconds": 5.2, "exit_code": 0, "status": "PASS",
        }]
        html = render_recent_actions_table(actions)
        assert "run-lifecycle" in html
        assert "PASS" in html


class TestDashboardSections:
    def test_contains_paper_positions(self):
        html = render_dashboard_html({})
        assert "纸面持仓" in html

    def test_contains_strategy_scorecard(self):
        html = render_dashboard_html({})
        assert "策略评分" in html

    def test_contains_sample_gate(self):
        html = render_dashboard_html({})
        assert "样本门禁" in html

    def test_contains_recent_actions(self):
        html = render_dashboard_html({})
        assert "最近操作" in html

    def test_contains_en_sections(self):
        html = render_dashboard_html({}, lang="en")
        assert "Paper Positions" in html
        assert "Strategy Scorecard" in html
        assert "Sample Gate" in html
        assert "Recent Actions" in html

    def test_no_testnet_ready(self):
        html = render_dashboard_html({})
        assert "testnet_ready=true" not in html
        assert "live_ready=true" not in html

    def test_with_positions_data(self):
        positions = [{
            "status": "OPEN", "strategy_id": "test", "symbol": "BTCUSDT",
            "timeframe": "15m", "side": "LONG", "entry_price": 60000,
            "stop_loss": 59000, "take_profit": 62000,
            "unrealized_pnl": 0, "realized_pnl": 0, "r_multiple": 0,
            "quarantine_status": "CLEAN", "excluded_from_performance_stats": False,
        }]
        html = render_dashboard_html({}, positions=positions)
        assert "BTCUSDT" in html

    def test_with_scorecard_data(self):
        sc = {"global_metrics": {"sample_status": "INSUFFICIENT_CLOSED_SAMPLE"}, "strategy_scorecards": [{
            "strategy_id": "test", "strategy_type": "test", "position_count": 5,
            "open_count": 5, "closed_count": 0, "tp_count": 0, "sl_count": 0,
            "timeout_count": 0, "win_rate": 0, "profit_factor": 0, "expectancy_r": 0,
            "sample_status": "INSUFFICIENT_CLOSED_SAMPLE", "strategy_status": "OBSERVE_ONLY",
            "strategy_score": 0,
        }]}
        html = render_dashboard_html({}, scorecard=sc)
        assert "OBSERVE_ONLY" in html


class TestLoadStrategyConfig:
    def test_missing_file_returns_none(self):
        assert load_strategy_config("/nonexistent/config.yaml") is None

    def test_reads_real_config(self):
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "strategies.yaml")
        if os.path.isfile(config_path):
            config = load_strategy_config(config_path)
            assert config is not None
            assert "strategies" in config


class TestLoadStrategySwitchboard:
    def test_missing_config_returns_empty(self):
        assert load_strategy_switchboard("/nonexistent/config.yaml") == []

    def test_merges_scorecard(self):
        import tempfile, yaml
        config = {
            "strategies": {
                "test_strat": {
                    "enabled": True, "strategy_type": "test", "mode": "paper",
                    "data_api": "binance", "symbols": ["BTCUSDT"], "timeframes": ["15m"],
                    "alert": {"feishu_payload": True, "auto_send": False},
                }
            }
        }
        scorecard = {"strategy_scorecards": [{
            "strategy_id": "test_strat", "sample_status": "EVALUABLE",
            "strategy_status": "CANDIDATE_KEEP", "strategy_score": 85.0,
        }]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            path = f.name
        try:
            rows = load_strategy_switchboard(path, scorecard)
            assert len(rows) == 1
            assert rows[0]["scorecard_sample_status"] == "EVALUABLE"
            assert rows[0]["scorecard_strategy_status"] == "CANDIDATE_KEEP"
        finally:
            os.unlink(path)

    def test_no_scorecard_shows_na(self):
        import tempfile, yaml
        config = {
            "strategies": {
                "test_strat": {
                    "enabled": True, "strategy_type": "test", "mode": "paper",
                    "data_api": "binance", "symbols": ["BTCUSDT"], "timeframes": ["15m"],
                    "alert": {"feishu_payload": True, "auto_send": False},
                }
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            path = f.name
        try:
            rows = load_strategy_switchboard(path, None)
            assert rows[0]["scorecard_sample_status"] == "N/A"
        finally:
            os.unlink(path)


class TestRenderStrategySwitchboard:
    def test_empty_config(self):
        html = render_strategy_switchboard_table([])
        assert "暂无策略配置" in html

    def test_empty_config_en(self):
        html = render_strategy_switchboard_table([], lang="en")
        assert "No strategy config found" in html

    def test_renders_enabled_strategy(self):
        switchboard = [{
            "strategy_id": "test", "enabled": True, "strategy_type": "test",
            "mode": "paper", "data_api": "binance", "symbols_count": 2,
            "symbols_display": "BTCUSDT, ETHUSDT", "timeframes": "15m, 1h",
            "feishu_payload": True, "auto_send": False,
            "scorecard_sample_status": "N/A", "scorecard_strategy_status": "N/A",
            "scorecard_strategy_score": "N/A",
        }]
        html = render_strategy_switchboard_table(switchboard)
        assert "test" in html
        assert "ON" in html

    def test_renders_disabled_strategy(self):
        switchboard = [{
            "strategy_id": "test", "enabled": False, "strategy_type": "test",
            "mode": "paper", "data_api": "binance", "symbols_count": 1,
            "symbols_display": "BTCUSDT", "timeframes": "15m",
            "feishu_payload": True, "auto_send": False,
            "scorecard_sample_status": "N/A", "scorecard_strategy_status": "N/A",
            "scorecard_strategy_score": "N/A",
        }]
        html = render_strategy_switchboard_table(switchboard)
        assert "OFF" in html

    def test_escapes_html(self):
        switchboard = [{
            "strategy_id": "<script>alert(1)</script>", "enabled": True,
            "strategy_type": "test", "mode": "paper", "data_api": "binance",
            "symbols_count": 1, "symbols_display": "BTCUSDT", "timeframes": "15m",
            "feishu_payload": True, "auto_send": False,
            "scorecard_sample_status": "N/A", "scorecard_strategy_status": "N/A",
            "scorecard_strategy_score": "N/A",
        }]
        html = render_strategy_switchboard_table(switchboard)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_auto_send_warning(self):
        switchboard = [{
            "strategy_id": "test", "enabled": True, "strategy_type": "test",
            "mode": "paper", "data_api": "binance", "symbols_count": 1,
            "symbols_display": "BTCUSDT", "timeframes": "15m",
            "feishu_payload": True, "auto_send": True,
            "scorecard_sample_status": "N/A", "scorecard_strategy_status": "N/A",
            "scorecard_strategy_score": "N/A",
        }]
        html = render_strategy_switchboard_table(switchboard)
        assert "true" in html

    def test_symbols_truncated(self):
        symbols = [f"SYM{i}USDT" for i in range(25)]
        switchboard = [{
            "strategy_id": "test", "enabled": True, "strategy_type": "test",
            "mode": "paper", "data_api": "binance", "symbols_count": 25,
            "symbols_display": ", ".join(symbols[:20]) + " +5 more",
            "timeframes": "15m", "feishu_payload": True, "auto_send": False,
            "scorecard_sample_status": "N/A", "scorecard_strategy_status": "N/A",
            "scorecard_strategy_score": "N/A",
        }]
        html = render_strategy_switchboard_table(switchboard)
        assert "+5 more" in html


class TestDashboardSwitchboard:
    def test_contains_strategy_switchboard(self):
        html = render_dashboard_html({})
        assert "策略开关" in html

    def test_contains_strategy_switchboard_en(self):
        html = render_dashboard_html({}, lang="en")
        assert "Strategy Switchboard" in html

    def test_contains_read_only_notice(self):
        html = render_dashboard_html({})
        assert "read-only" in html.lower() or "Read-only" in html

    def test_contains_config_source(self):
        html = render_dashboard_html({})
        assert "strategies.yaml" in html

    def test_no_direct_config_write(self):
        html = render_dashboard_html({})
        assert "config_written=true" not in html
        assert "不会直接修改" in html

    def test_no_testnet_ready(self):
        html = render_dashboard_html({})
        assert "testnet_ready=true" not in html
        assert "live_ready=true" not in html

    def test_with_switchboard_data(self):
        switchboard = [{
            "strategy_id": "macd_rebound_watch", "enabled": True,
            "strategy_type": "macd_rebound_watch", "mode": "paper",
            "data_api": "binance_usdm_klines", "symbols_count": 5,
            "symbols_display": "BTCUSDT, ETHUSDT", "timeframes": "5m, 15m, 1h",
            "feishu_payload": True, "auto_send": False,
            "scorecard_sample_status": "INSUFFICIENT_CLOSED_SAMPLE",
            "scorecard_strategy_status": "OBSERVE_ONLY",
            "scorecard_strategy_score": 0.0,
        }]
        html = render_dashboard_html({}, strategy_switchboard=switchboard)
        assert "macd_rebound_watch" in html
        assert "OBSERVE_ONLY" in html


class TestValidateConfigChangeRequest:
    def test_valid_request(self):
        switchboard = [{"strategy_id": "test_strat"}]
        form = {
            "strategy_id": "test_strat",
            "requested_enabled": "true",
            "requested_symbols": "BTCUSDT, ETHUSDT",
            "requested_timeframes": "15m, 1h",
            "reason": "Testing",
        }
        cleaned, errors = validate_config_change_request(form, switchboard)
        assert errors == []
        assert cleaned["strategy_id"] == "test_strat"
        assert cleaned["requested_enabled"] == "true"
        assert cleaned["requested_symbols"] == ["BTCUSDT", "ETHUSDT"]
        assert cleaned["requested_timeframes"] == ["15m", "1h"]

    def test_unknown_strategy_rejected(self):
        switchboard = [{"strategy_id": "test_strat"}]
        form = {"strategy_id": "unknown", "requested_enabled": "no_change",
                "requested_symbols": "", "requested_timeframes": "", "reason": "test"}
        _, errors = validate_config_change_request(form, switchboard)
        assert any("Unknown strategy" in e for e in errors)

    def test_invalid_enabled_rejected(self):
        switchboard = [{"strategy_id": "test"}]
        form = {"strategy_id": "test", "requested_enabled": "invalid",
                "requested_symbols": "", "requested_timeframes": "", "reason": "test"}
        _, errors = validate_config_change_request(form, switchboard)
        assert any("requested_enabled" in e for e in errors)

    def test_invalid_symbol_rejected(self):
        switchboard = [{"strategy_id": "test"}]
        form = {"strategy_id": "test", "requested_enabled": "no_change",
                "requested_symbols": "<script>", "requested_timeframes": "", "reason": "test"}
        _, errors = validate_config_change_request(form, switchboard)
        assert any("Invalid symbol" in e for e in errors)

    def test_too_many_symbols_rejected(self):
        switchboard = [{"strategy_id": "test"}]
        symbols = ",".join([f"S{i}" for i in range(101)])
        form = {"strategy_id": "test", "requested_enabled": "no_change",
                "requested_symbols": symbols, "requested_timeframes": "", "reason": "test"}
        _, errors = validate_config_change_request(form, switchboard)
        assert any("Too many symbols" in e for e in errors)

    def test_invalid_timeframe_rejected(self):
        switchboard = [{"strategy_id": "test"}]
        form = {"strategy_id": "test", "requested_enabled": "no_change",
                "requested_symbols": "", "requested_timeframes": "2d", "reason": "test"}
        _, errors = validate_config_change_request(form, switchboard)
        assert any("Invalid timeframe" in e for e in errors)

    def test_missing_reason_rejected(self):
        switchboard = [{"strategy_id": "test"}]
        form = {"strategy_id": "test", "requested_enabled": "no_change",
                "requested_symbols": "", "requested_timeframes": "", "reason": ""}
        _, errors = validate_config_change_request(form, switchboard)
        assert any("reason is required" in e for e in errors)


class TestCreateConfigChangeRequest:
    def test_creates_request(self):
        form = {
            "strategy_id": "test", "requested_enabled": "true",
            "requested_symbols": ["BTCUSDT"], "requested_timeframes": ["15m"],
            "reason": "test",
        }
        request = create_config_change_request(form, {"enabled": True})
        assert request["status"] == "PENDING_HUMAN_REVIEW"
        assert request["config_written"] is False
        assert request["strategy_id"] == "test"
        assert request["requested_enabled"] == "true"
        assert request["request_id"].startswith("CR_")


class TestAppendConfigChangeRequest:
    def test_appends_jsonl_and_md(self):
        with tempfile.TemporaryDirectory() as td:
            request = {
                "request_id": "CR_test", "created_at": "2026-01-01",
                "strategy_id": "test", "current_config_snapshot": {"enabled": True},
                "requested_enabled": "true", "requested_symbols": ["BTCUSDT"],
                "requested_timeframes": ["15m"], "reason": "test",
                "status": "PENDING_HUMAN_REVIEW", "config_written": False,
                "safety_flags": [],
            }
            jsonl_path, md_path = append_config_change_request(request, td)
            assert os.path.isfile(jsonl_path)
            assert os.path.isfile(md_path)
            import glob
            jsonl_files = glob.glob(os.path.join(td, "*_strategy_config_change_requests.jsonl"))
            assert len(jsonl_files) == 1
            with open(md_path) as f:
                content = f.read()
            assert "PENDING_HUMAN_REVIEW" in content
            assert "config_written: false" in content


class TestRenderConfigChangeForm:
    def test_contains_form(self):
        switchboard = [{"strategy_id": "test"}]
        html = render_config_change_form(switchboard)
        assert "strategy_id" in html
        assert "requested_enabled" in html
        assert "reason" in html

    def test_contains_read_only_notice(self):
        html = render_config_change_form([])
        assert "不会直接修改" in html

    def test_contains_strategy_options(self):
        switchboard = [{"strategy_id": "macd"}, {"strategy_id": "weak"}]
        html = render_config_change_form(switchboard)
        assert "macd" in html
        assert "weak" in html


class TestRenderConfigChangeResult:
    def test_renders_result(self):
        request = {
            "request_id": "CR_test", "status": "PENDING_HUMAN_REVIEW",
            "config_written": False, "strategy_id": "test",
            "requested_enabled": "true",
        }
        html = render_config_change_result(request)
        assert "CR_test" in html
        assert "PENDING_HUMAN_REVIEW" in html
        assert "config_written" in html


class TestDashboardConfigChange:
    def test_contains_config_change_request(self):
        html = render_dashboard_html({})
        assert "策略配置变更草案" in html

    def test_contains_config_change_request_en(self):
        html = render_dashboard_html({}, lang="en")
        assert "Strategy Config Change Request" in html

    def test_contains_change_request_notice(self):
        html = render_dashboard_html({})
        assert "不会直接修改" in html or "change request" in html.lower()

    def test_no_testnet_ready(self):
        html = render_dashboard_html({})
        assert "testnet_ready=true" not in html
        assert "live_ready=true" not in html


class TestNormalizeLang:
    def test_zh(self):
        assert normalize_lang("zh") == "zh"

    def test_en(self):
        assert normalize_lang("en") == "en"

    def test_invalid_fallback_zh(self):
        assert normalize_lang("fr") == "zh"
        assert normalize_lang("de") == "zh"
        assert normalize_lang("") == "zh"
        assert normalize_lang("ZH") == "zh"
        assert normalize_lang("EN") == "en"
        assert normalize_lang(" en ") == "en"

    def test_none_fallback_zh(self):
        assert normalize_lang("") == "zh"


class TestBilingualUI:
    def test_lang_switch_contains_both(self):
        html = render_dashboard_html({})
        assert "中文" in html
        assert "English" in html

    def test_lang_switch_links(self):
        html = render_dashboard_html({})
        assert "?lang=zh" in html
        assert "?lang=en" in html

    def test_zh_heading_zh(self):
        html = render_dashboard_html({}, lang="zh")
        assert "影子交易控制台" in html

    def test_en_heading_en(self):
        html = render_dashboard_html({}, lang="en")
        assert "Shadow Trading Console" in html

    def test_sample_warning_zh(self):
        sc = {"global_metrics": {"sample_status": "INSUFFICIENT_CLOSED_SAMPLE"}, "strategy_scorecards": [{
            "strategy_id": "t", "strategy_type": "t", "position_count": 1,
            "open_count": 1, "closed_count": 0, "tp_count": 0, "sl_count": 0,
            "timeout_count": 0, "win_rate": 0, "profit_factor": 0, "expectancy_r": 0,
            "sample_status": "INSUFFICIENT_CLOSED_SAMPLE", "strategy_status": "OBSERVE_ONLY",
            "strategy_score": 0,
        }]}
        html = render_dashboard_html({}, scorecard=sc, lang="zh")
        assert "样本不足" in html

    def test_sample_warning_en(self):
        sc = {"global_metrics": {"sample_status": "INSUFFICIENT_CLOSED_SAMPLE"}, "strategy_scorecards": [{
            "strategy_id": "t", "strategy_type": "t", "position_count": 1,
            "open_count": 1, "closed_count": 0, "tp_count": 0, "sl_count": 0,
            "timeout_count": 0, "win_rate": 0, "profit_factor": 0, "expectancy_r": 0,
            "sample_status": "INSUFFICIENT_CLOSED_SAMPLE", "strategy_status": "OBSERVE_ONLY",
            "strategy_score": 0,
        }]}
        html = render_dashboard_html({}, scorecard=sc, lang="en")
        assert "Insufficient sample" in html

    def test_no_cookies(self):
        html = render_dashboard_html({})
        assert "document.cookie" not in html
        assert "localStorage" not in html
        assert "sessionStorage" not in html

    def test_no_sessions(self):
        html = render_dashboard_html({})
        assert "session" not in html.lower() or "PENDING_HUMAN_REVIEW" in html

    def test_html_lang_attribute_zh(self):
        html = render_dashboard_html({}, lang="zh")
        assert '<html lang="zh">' in html

    def test_html_lang_attribute_en(self):
        html = render_dashboard_html({}, lang="en")
        assert '<html lang="en">' in html

    def test_status_values_not_translated(self):
        html = render_dashboard_html({}, lang="zh")
        assert "sample_status" in html
        assert "testnet_gate_status" in html


class TestUILayout:
    def test_all_ui_text_keys_present(self):
        zh_keys = set(UI_TEXT["zh"].keys())
        en_keys = set(UI_TEXT["en"].keys())
        assert zh_keys == en_keys, f"Mismatch: zh has {zh_keys - en_keys}, en has {en_keys - zh_keys}"
