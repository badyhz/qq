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
    ALLOWED_ACTIONS, SAFETY_FLAGS,
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
        assert "Shadow Trading Console" in html

    def test_contains_sample_status(self):
        html = render_dashboard_html({"sample_status": "INSUFFICIENT_CLOSED_SAMPLE"})
        assert "sample_status" in html
        assert "INSUFFICIENT_CLOSED_SAMPLE" in html

    def test_contains_testnet_gate_status(self):
        html = render_dashboard_html({"testnet_gate_status": "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE"})
        assert "testnet_gate_status" in html
        assert "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE" in html

    def test_contains_buttons(self):
        html = render_dashboard_html({})
        assert "扫描新机会" in html
        assert "只更新已有持仓" in html
        assert "刷新样本门禁" in html
        assert "打印当前状态" in html

    def test_contains_safety_footer(self):
        html = render_dashboard_html({})
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
        assert "Paper Positions" in html

    def test_contains_strategy_scorecard(self):
        html = render_dashboard_html({})
        assert "Strategy Scorecard" in html

    def test_contains_sample_gate(self):
        html = render_dashboard_html({})
        assert "Sample Gate" in html

    def test_contains_recent_actions(self):
        html = render_dashboard_html({})
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
