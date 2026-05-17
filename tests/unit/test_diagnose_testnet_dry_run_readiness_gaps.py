import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.diagnose_testnet_dry_run_readiness_gaps import (
    _severity_for_gap,
    _build_numeric_gap,
    _build_bool_gap,
    diagnose_testnet_dry_run_readiness_gaps,
)


class TestSeverityForGap:
    def test_zero_or_negative_returns_none(self):
        assert _severity_for_gap(0.0) == "NONE"
        assert _severity_for_gap(-1.0) == "NONE"

    def test_critical_flag_overrides(self):
        assert _severity_for_gap(1.0, is_critical=True) == "CRITICAL"

    def test_gap_ge_10_is_critical(self):
        assert _severity_for_gap(10.0) == "CRITICAL"
        assert _severity_for_gap(15.0) == "CRITICAL"

    def test_gap_ge_3_is_high(self):
        assert _severity_for_gap(3.0) == "HIGH"
        assert _severity_for_gap(5.0) == "HIGH"
        assert _severity_for_gap(9.9) == "HIGH"

    def test_gap_ge_1_is_medium(self):
        assert _severity_for_gap(1.0) == "MEDIUM"
        assert _severity_for_gap(2.5) == "MEDIUM"

    def test_gap_lt_1_is_low(self):
        assert _severity_for_gap(0.1) == "LOW"
        assert _severity_for_gap(0.99) == "LOW"


class TestBuildNumericGap:
    def test_no_gap_when_current_meets_required(self):
        result = _build_numeric_gap(
            requirement_key="test_key",
            requirement_name="Test",
            current_value=10.0,
            required_value=5.0,
            gap_unit="samples",
            priority="P1",
            remediation_hint="collect more",
            source_report="test.csv",
        )
        assert result["gap_value"] == 0.0
        assert result["gap_severity"] == "NONE"
        assert result["blocking"] is False
        assert result["priority"] == "P3"

    def test_gap_when_current_below_required(self):
        result = _build_numeric_gap(
            requirement_key="test_key",
            requirement_name="Test",
            current_value=3.0,
            required_value=10.0,
            gap_unit="samples",
            priority="P0",
            remediation_hint="collect more",
            source_report="test.csv",
            critical=True,
        )
        assert result["gap_value"] == 7.0
        assert result["gap_severity"] == "CRITICAL"
        assert result["blocking"] is True
        assert result["priority"] == "P0"

    def test_fields_are_preserved(self):
        result = _build_numeric_gap(
            requirement_key="rk1",
            requirement_name="Req Name",
            current_value=1.5,
            required_value=2.0,
            gap_unit="days",
            priority="P2",
            remediation_hint="hint text",
            source_report="src.json",
        )
        assert result["requirement_key"] == "rk1"
        assert result["requirement_name"] == "Req Name"
        assert result["current_value"] == 1.5
        assert result["required_value"] == 2.0
        assert result["gap_unit"] == "days"
        assert result["remediation_hint"] == "hint text"
        assert result["source_report"] == "src.json"


class TestBuildBoolGap:
    def test_pass_when_ok(self):
        result = _build_bool_gap(
            requirement_key="bk",
            requirement_name="Bool Test",
            current_ok=True,
            priority="P2",
            remediation_hint="fix it",
            source_report="r.json",
        )
        assert result["gap_value"] == 0.0
        assert result["gap_severity"] == "NONE"
        assert result["blocking"] is False
        assert result["priority"] == "P3"

    def test_fail_when_not_ok(self):
        result = _build_bool_gap(
            requirement_key="bk",
            requirement_name="Bool Test",
            current_ok=False,
            priority="P1",
            remediation_hint="fix it",
            source_report="r.json",
        )
        assert result["gap_value"] == 1.0
        assert result["gap_severity"] == "LOW"
        assert result["blocking"] is True
        assert result["priority"] == "P1"

    def test_current_value_is_bool(self):
        result = _build_bool_gap(
            requirement_key="bk",
            requirement_name="Bool Test",
            current_ok=True,
            priority="P2",
            remediation_hint="fix it",
            source_report="r.json",
        )
        assert result["current_value"] is True
        assert result["required_value"] is True


class TestDiagnoseIntegration:
    def test_empty_inputs_produces_not_ready(self, tmp_path):
        out_dir = tmp_path / "output"
        phase_json = tmp_path / "phase.json"
        phase_json.write_text(json.dumps({}))
        history_csv = tmp_path / "history.csv"
        history_csv.write_text("run_date\n")
        dashboard_json = tmp_path / "dashboard.json"
        dashboard_json.write_text(json.dumps({}))
        stability_json = tmp_path / "stability.json"
        stability_json.write_text(json.dumps({}))
        strategy_json = tmp_path / "strategy.json"
        strategy_json.write_text(json.dumps({}))
        daily_json = tmp_path / "daily.json"
        daily_json.write_text(json.dumps({}))

        result = diagnose_testnet_dry_run_readiness_gaps(
            phase_review_json=str(phase_json),
            shadow_research_history_csv=str(history_csv),
            experiment_history_dashboard_json=str(dashboard_json),
            experiment_stability_summary_json=str(stability_json),
            strategy_candidate_score_summary_json=str(strategy_json),
            daily_shadow_research_control_json=str(daily_json),
            output_dir=str(out_dir),
        )
        assert result["final_verdict"] == "NOT_READY"
        assert result["blocking_gap_count"] > 0
        assert result["submit_attempted"] is False
        assert result["cancel_attempted"] is False
        assert result["flatten_attempted"] is False

    def test_outputs_csv_and_json(self, tmp_path):
        out_dir = tmp_path / "output"
        phase_json = tmp_path / "phase.json"
        phase_json.write_text(json.dumps({"minimum_requirements": {"system_health_pass": True, "no_trade_actions_attempted": True, "testnet_dry_run_readiness_not_fail": True}}))
        history_csv = tmp_path / "history.csv"
        history_csv.write_text("run_date\n2026-01-01\n2026-01-02\n2026-01-03\n")
        dashboard_json = tmp_path / "dashboard.json"
        dashboard_json.write_text(json.dumps({"history_row_count": 25}))
        stability_json = tmp_path / "stability.json"
        stability_json.write_text(json.dumps({"experiment_count": 5, "needs_more_data_count": 2}))
        strategy_json = tmp_path / "strategy.json"
        strategy_json.write_text(json.dumps({"avg_weighted_sample_count": 10}))
        daily_json = tmp_path / "daily.json"
        daily_json.write_text(json.dumps({"submit_attempted": False, "cancel_attempted": False, "flatten_attempted": False}))

        result = diagnose_testnet_dry_run_readiness_gaps(
            phase_review_json=str(phase_json),
            shadow_research_history_csv=str(history_csv),
            experiment_history_dashboard_json=str(dashboard_json),
            experiment_stability_summary_json=str(stability_json),
            strategy_candidate_score_summary_json=str(strategy_json),
            daily_shadow_research_control_json=str(daily_json),
            output_dir=str(out_dir),
        )
        assert (out_dir / "readiness_gaps.csv").exists()
        assert (out_dir / "summary.json").exists()
        assert (out_dir / "summary.md").exists()
        assert result["final_verdict"] in ("READY", "NOT_READY")