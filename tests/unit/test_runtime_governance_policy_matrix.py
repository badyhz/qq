"""Tests for core.runtime_governance_policy_matrix."""

import pytest

from core.runtime_governance_policy_matrix import (
    RuntimeGovernancePolicyCase,
    build_runtime_governance_policy_matrix,
    evaluate_runtime_governance_policy_case,
    policy_matrix_to_dict,
    policy_matrix_to_markdown,
)


class TestShadowNoSubmit:
    def test_shadow_blocks_submit(self):
        allowed, reason = evaluate_runtime_governance_policy_case(
            "shadow", "test", False, True, False,
        )
        assert not allowed
        assert "shadow" in reason and "submit" in reason

    def test_shadow_allows_offline(self):
        allowed, reason = evaluate_runtime_governance_policy_case(
            "shadow", "test", False, False, False,
        )
        assert allowed


class TestDryRunNoSubmit:
    def test_dry_run_blocks_submit(self):
        allowed, reason = evaluate_runtime_governance_policy_case(
            "dry_run", "testnet", False, True, False,
        )
        assert not allowed
        assert "dry_run" in reason and "submit" in reason

    def test_dry_run_allows_no_submit(self):
        allowed, reason = evaluate_runtime_governance_policy_case(
            "dry_run", "test", False, False, False,
        )
        assert allowed


class TestTestnetSubmitSimulatedEnv:
    def test_allowed_in_test(self):
        allowed, reason = evaluate_runtime_governance_policy_case(
            "testnet_submit_simulated", "test", True, True, False,
        )
        assert allowed

    def test_allowed_in_testnet(self):
        allowed, reason = evaluate_runtime_governance_policy_case(
            "testnet_submit_simulated", "testnet", True, True, False,
        )
        assert allowed

    def test_blocked_in_local(self):
        allowed, _ = evaluate_runtime_governance_policy_case(
            "testnet_submit_simulated", "local", True, True, False,
        )
        assert not allowed


class TestProdSubmitBlockedAlways:
    @pytest.mark.parametrize("mode", ["shadow", "dry_run", "testnet_dry", "testnet_submit_simulated"])
    def test_prod_always_blocked(self, mode):
        allowed, reason = evaluate_runtime_governance_policy_case(
            mode, "prod", True, True, False,
        )
        assert not allowed
        assert "prod" in reason


class TestMatrixDeterministic:
    def test_repeated_calls_identical(self):
        m1 = build_runtime_governance_policy_matrix()
        m2 = build_runtime_governance_policy_matrix()
        assert m1 == m2

    def test_markdown_deterministic(self):
        m = build_runtime_governance_policy_matrix()
        md1 = policy_matrix_to_markdown(m)
        md2 = policy_matrix_to_markdown(m)
        assert md1 == md2


class TestEvaluateMatchesMatrix:
    def test_all_entries_match(self):
        matrix = build_runtime_governance_policy_matrix()
        for case in matrix:
            allowed, reason = evaluate_runtime_governance_policy_case(
                case.mode,
                case.environment,
                case.allow_network,
                case.allow_submit,
                case.allow_file_io,
            )
            assert allowed == case.expected_allowed, (
                f"Mismatch for {case.mode}/{case.environment}: "
                f"evaluate={allowed}, matrix={case.expected_allowed}"
            )
            assert reason == case.expected_reason


class TestPolicyMatrixToDict:
    def test_returns_list_of_dicts(self):
        matrix = build_runtime_governance_policy_matrix()
        result = policy_matrix_to_dict(matrix)
        assert isinstance(result, list)
        assert len(result) == len(matrix)
        for d in result:
            assert isinstance(d, dict)
            assert "mode" in d
            assert "expected_allowed" in d


class TestMatrixSize:
    def test_at_least_16_cases(self):
        matrix = build_runtime_governance_policy_matrix()
        assert len(matrix) >= 16
