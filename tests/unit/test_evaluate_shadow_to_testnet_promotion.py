import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.evaluate_shadow_to_testnet_promotion import (
    _decide_promotion,
    evaluate_shadow_to_testnet_promotion,
)


def _nan():
    return float("nan")


class TestDecidePromotion:
    def test_reject_negative_shadow_expectancy(self):
        result = _decide_promotion(
            real_count=0,
            shadow_count=25,
            weighted_count=7.5,
            shadow_avg_r=-0.5,
            weighted_avg_r=-0.15,
            system_health_verdict="PASS",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] == "REJECT_SHADOW_STRATEGY"
        assert result["allowed_action"] == "BLOCKED"
        assert result["submit_permission"] == "NO_TESTNET_SUBMIT"
        assert result["risk_level"] == "NEGATIVE_SHADOW_EDGE"
        assert "shadow_expectancy_negative" in result["reason"]

    def test_reject_shadow_avg_r_exactly_negative_threshold(self):
        result = _decide_promotion(
            real_count=0,
            shadow_count=20,
            weighted_count=6.0,
            shadow_avg_r=-0.21,
            weighted_avg_r=-0.06,
            system_health_verdict="PASS",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] == "REJECT_SHADOW_STRATEGY"

    def test_reject_not_triggered_when_shadow_count_below_20(self):
        result = _decide_promotion(
            real_count=0,
            shadow_count=19,
            weighted_count=5.7,
            shadow_avg_r=-0.5,
            weighted_avg_r=-0.15,
            system_health_verdict="PASS",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] != "REJECT_SHADOW_STRATEGY"

    def test_keep_shadow_only_weighted_count_nan(self):
        result = _decide_promotion(
            real_count=0,
            shadow_count=10,
            weighted_count=_nan(),
            shadow_avg_r=0.1,
            weighted_avg_r=_nan(),
            system_health_verdict="PASS",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] == "KEEP_SHADOW_ONLY"
        assert result["risk_level"] == "LOW_SAMPLE"
        assert "need_more_shadow_samples" in result["reason"]

    def test_keep_shadow_only_weighted_count_below_5(self):
        result = _decide_promotion(
            real_count=0,
            shadow_count=10,
            weighted_count=3.0,
            shadow_avg_r=0.1,
            weighted_avg_r=0.03,
            system_health_verdict="PASS",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] == "KEEP_SHADOW_ONLY"

    def test_keep_shadow_only_zero_shadow_count(self):
        result = _decide_promotion(
            real_count=0,
            shadow_count=0,
            weighted_count=0.0,
            shadow_avg_r=_nan(),
            weighted_avg_r=_nan(),
            system_health_verdict="PASS",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] == "KEEP_SHADOW_ONLY"

    def test_allow_testnet_dry_run_positive_weighted_low_real(self):
        result = _decide_promotion(
            real_count=1,
            shadow_count=20,
            weighted_count=7.0,
            shadow_avg_r=0.05,
            weighted_avg_r=0.15,
            system_health_verdict="PASS",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] == "ALLOW_TESTNET_DRY_RUN"
        assert result["allowed_action"] == "TESTNET_DRY_RUN_ONLY"
        assert result["submit_permission"] == "NO_TESTNET_SUBMIT"
        assert result["risk_level"] == "LOW_REAL_SAMPLE"
        assert "weighted_positive_but_real_too_small" in result["reason"]

    def test_allow_testnet_dry_run_requires_system_health_pass(self):
        result = _decide_promotion(
            real_count=1,
            shadow_count=20,
            weighted_count=7.0,
            shadow_avg_r=0.05,
            weighted_avg_r=0.15,
            system_health_verdict="FAIL",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] != "ALLOW_TESTNET_DRY_RUN"

    def test_allow_small_size_after_reset_full_conditions(self):
        result = _decide_promotion(
            real_count=5,
            shadow_count=60,
            weighted_count=23.0,
            shadow_avg_r=0.1,
            weighted_avg_r=0.35,
            system_health_verdict="PASS",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] == "ALLOW_TESTNET_SMALL_SIZE_AFTER_RESET"
        assert result["allowed_action"] == "TESTNET_SMALL_SIZE_ALLOWED_AFTER_RESET"
        assert result["submit_permission"] == "TESTNET_SUBMIT_ALLOWED_AFTER_RESET"
        assert result["risk_level"] == "CONTROLLED"
        assert "meets_shadow_to_testnet_threshold" in result["reason"]

    def test_allow_small_size_blocked_by_reset_readiness_fail(self):
        result = _decide_promotion(
            real_count=5,
            shadow_count=60,
            weighted_count=23.0,
            shadow_avg_r=0.1,
            weighted_avg_r=0.35,
            system_health_verdict="PASS",
            reset_readiness_verdict="FAIL",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] != "ALLOW_TESTNET_SMALL_SIZE_AFTER_RESET"

    def test_allow_small_size_blocked_by_cannot_submit_after_reset(self):
        result = _decide_promotion(
            real_count=5,
            shadow_count=60,
            weighted_count=23.0,
            shadow_avg_r=0.1,
            weighted_avg_r=0.35,
            system_health_verdict="PASS",
            reset_readiness_verdict="READY",
            can_submit_after_reset=False,
        )
        assert result["promotion_decision"] != "ALLOW_TESTNET_SMALL_SIZE_AFTER_RESET"

    def test_allow_small_size_blocked_by_weighted_avg_r_below_threshold(self):
        result = _decide_promotion(
            real_count=5,
            shadow_count=60,
            weighted_count=23.0,
            shadow_avg_r=0.1,
            weighted_avg_r=0.15,
            system_health_verdict="PASS",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] != "ALLOW_TESTNET_SMALL_SIZE_AFTER_RESET"

    def test_require_more_real_samples(self):
        result = _decide_promotion(
            real_count=2,
            shadow_count=15,
            weighted_count=6.0,
            shadow_avg_r=0.05,
            weighted_avg_r=0.05,
            system_health_verdict="FAIL",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] == "REQUIRE_MORE_REAL_SAMPLES"
        assert result["allowed_action"] == "TESTNET_DRY_RUN_ONLY"
        assert "require_more_real_samples" in result["reason"]

    def test_default_conservative_keep_shadow_only(self):
        result = _decide_promotion(
            real_count=5,
            shadow_count=15,
            weighted_count=6.0,
            shadow_avg_r=0.05,
            weighted_avg_r=0.05,
            system_health_verdict="FAIL",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] == "KEEP_SHADOW_ONLY"
        assert result["risk_level"] == "CONSERVATIVE"
        assert "default_shadow_collection" in result["reason"]

    def test_safety_cap_real_count_zero_gets_dry_run_via_third_elif(self):
        result = _decide_promotion(
            real_count=0,
            shadow_count=60,
            weighted_count=23.0,
            shadow_avg_r=0.1,
            weighted_avg_r=0.35,
            system_health_verdict="PASS",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] == "ALLOW_TESTNET_DRY_RUN"
        assert result["submit_permission"] == "NO_TESTNET_SUBMIT"
        assert "weighted_positive_but_real_too_small" in result["reason"]

    def test_safety_cap_real_count_below_3_gets_dry_run_via_third_elif(self):
        result = _decide_promotion(
            real_count=2,
            shadow_count=60,
            weighted_count=23.0,
            shadow_avg_r=0.1,
            weighted_avg_r=0.35,
            system_health_verdict="PASS",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] == "ALLOW_TESTNET_DRY_RUN"
        assert "weighted_positive_but_real_too_small" in result["reason"]

    def test_safety_cap_shadow_high_real_zero_gets_dry_run_via_third_elif(self):
        result = _decide_promotion(
            real_count=0,
            shadow_count=55,
            weighted_count=23.0,
            shadow_avg_r=0.1,
            weighted_avg_r=0.35,
            system_health_verdict="PASS",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] == "ALLOW_TESTNET_DRY_RUN"
        assert "weighted_positive_but_real_too_small" in result["reason"]

    def test_safety_caps_not_applied_when_not_small_size(self):
        result = _decide_promotion(
            real_count=0,
            shadow_count=55,
            weighted_count=3.0,
            shadow_avg_r=0.1,
            weighted_avg_r=0.03,
            system_health_verdict="PASS",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        assert result["promotion_decision"] == "KEEP_SHADOW_ONLY"

    def test_all_fields_present_in_result(self):
        result = _decide_promotion(
            real_count=0,
            shadow_count=10,
            weighted_count=3.0,
            shadow_avg_r=0.1,
            weighted_avg_r=0.03,
            system_health_verdict="PASS",
            reset_readiness_verdict="READY",
            can_submit_after_reset=True,
        )
        for key in ["promotion_decision", "allowed_action", "submit_permission", "risk_level", "reason"]:
            assert key in result


class TestEvaluateIntegration:
    def test_empty_inputs_produces_partial(self, tmp_path):
        out_dir = tmp_path / "output"
        rvs_csv = tmp_path / "rvs.csv"
        rvs_csv.write_text("strategy_key,symbol,real_sample_count,shadow_sample_count,weighted_sample_count,real_avg_r,shadow_avg_r,weighted_avg_r\n")
        strategy_csv = tmp_path / "strategy.csv"
        strategy_csv.write_text("strategy_key,sample_confidence_level\n")
        reset_json = tmp_path / "reset.json"
        reset_json.write_text(json.dumps({}))
        health_json = tmp_path / "health.json"
        health_json.write_text(json.dumps({}))

        result = evaluate_shadow_to_testnet_promotion(
            real_vs_shadow_csv=str(rvs_csv),
            strategy_candidate_csv=str(strategy_csv),
            testnet_reset_readiness_json=str(reset_json),
            system_health_json=str(health_json),
            output_dir=str(out_dir),
        )
        assert result["final_verdict"] == "PARTIAL"
        assert result["strategy_count"] == 0

    def test_single_row_produces_output_files(self, tmp_path):
        out_dir = tmp_path / "output"
        rvs_csv = tmp_path / "rvs.csv"
        rvs_csv.write_text(
            "strategy_key,symbol,real_sample_count,shadow_sample_count,weighted_sample_count,real_avg_r,shadow_avg_r,weighted_avg_r\n"
            "SK1,BTCUSDT,0,25,7.5,0,0.1,0.15\n"
        )
        strategy_csv = tmp_path / "strategy.csv"
        strategy_csv.write_text("strategy_key,sample_confidence_level\nSK1,MEDIUM\n")
        reset_json = tmp_path / "reset.json"
        reset_json.write_text(json.dumps({"readiness_verdict": "READY", "can_submit_after_reset": True}))
        health_json = tmp_path / "health.json"
        health_json.write_text(json.dumps({"final_verdict": "PASS"}))

        result = evaluate_shadow_to_testnet_promotion(
            real_vs_shadow_csv=str(rvs_csv),
            strategy_candidate_csv=str(strategy_csv),
            testnet_reset_readiness_json=str(reset_json),
            system_health_json=str(health_json),
            output_dir=str(out_dir),
        )
        assert result["final_verdict"] == "PASS"
        assert result["strategy_count"] == 1
        assert (out_dir / "shadow_to_testnet_promotion.csv").exists()
        assert (out_dir / "summary.json").exists()
        assert (out_dir / "summary.md").exists()

    def test_missing_input_files_handled_gracefully(self, tmp_path):
        out_dir = tmp_path / "output"
        result = evaluate_shadow_to_testnet_promotion(
            real_vs_shadow_csv=str(tmp_path / "nonexistent.csv"),
            strategy_candidate_csv=str(tmp_path / "nonexistent2.csv"),
            testnet_reset_readiness_json=str(tmp_path / "nonexistent3.json"),
            system_health_json=str(tmp_path / "nonexistent4.json"),
            output_dir=str(out_dir),
        )
        assert result["final_verdict"] == "PARTIAL"
        assert result["strategy_count"] == 0