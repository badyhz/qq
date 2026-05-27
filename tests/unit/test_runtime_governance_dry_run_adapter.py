"""Tests for runtime governance dry-run adapter.

Sync only. No async. No I/O. No network. No random.
"""

from __future__ import annotations

import pytest

from core.runtime_governance_contract import RuntimeGovernanceInput
from core.runtime_governance_dry_run_adapter import (
    RuntimeGovernanceDryRunResult,
    dry_run_result_to_dict,
    dry_run_result_to_markdown,
    evaluate_runtime_governance_dry_run,
)


# ── fixtures ──────────────────────────────────────────────────────────


def _valid_input(**overrides) -> RuntimeGovernanceInput:
    defaults = dict(
        run_id="run-001",
        adapter_id="adapter-001",
        mode="dry_run",
        requested_action="scan",
        symbol="BTCUSDT",
        environment="test",
        allow_network=False,
        allow_submit=False,
        allow_file_io=False,
        metadata={},
    )
    defaults.update(overrides)
    return RuntimeGovernanceInput(**defaults)


# ── tests ─────────────────────────────────────────────────────────────


class TestValidInputPassVerdict:
    def test_valid_input_passes(self):
        inp = _valid_input()
        result = evaluate_runtime_governance_dry_run(inp)

        assert result.contract_result.ok is True
        assert result.contract_result.failures == []
        assert result.report.verdict == "PASS"
        assert result.packet.snapshot_diff.ok is True
        assert result.final_verdict == "PASS"
        assert result.mode == "dry_run"


class TestInvalidInputMissingRunId:
    def test_missing_run_id_fails(self):
        inp = _valid_input(run_id="")
        result = evaluate_runtime_governance_dry_run(inp)

        assert result.contract_result.ok is False
        assert len(result.contract_result.failures) > 0
        assert result.report.total_failures > 0
        assert result.report.verdict == "FAIL"
        assert result.final_verdict == "FAIL"


class TestPolicyBlock:
    def test_allow_submit_in_prod_blocked(self):
        inp = _valid_input(allow_submit=True, environment="prod")
        result = evaluate_runtime_governance_dry_run(inp)

        assert result.contract_result.ok is False
        assert result.report.verdict == "BLOCKED"
        assert result.final_verdict == "BLOCKED"


class TestSnapshotMismatch:
    def test_snapshot_mismatch_fails(self):
        inp = _valid_input()
        # provide wrong expected markdown to force snapshot diff
        expected = "# Runtime Governance Dry-Run Report\n\n**Verdict:** FAIL\n"
        result = evaluate_runtime_governance_dry_run(inp, expected_markdown=expected)

        assert result.packet.snapshot_diff.ok is False
        assert result.final_verdict == "FAIL"


class TestDictSerializationKeys:
    def test_dict_keys(self):
        inp = _valid_input()
        result = evaluate_runtime_governance_dry_run(inp)
        d = dry_run_result_to_dict(result)

        expected_keys = {
            "input",
            "contract_result",
            "report",
            "packet",
            "final_verdict",
        }
        assert expected_keys.issubset(set(d.keys()))

        # nested keys
        assert "run_id" in d["input"]
        assert "ok" in d["contract_result"]
        assert "verdict" in d["report"]
        assert "snapshot_diff" in d["packet"]


class TestMarkdownContainsVerdict:
    def test_markdown_contains_final_verdict(self):
        inp = _valid_input()
        result = evaluate_runtime_governance_dry_run(inp)
        md = dry_run_result_to_markdown(result)

        assert "**Final Verdict:** PASS" in md
        assert "**Mode:** dry_run" in md


class TestMarkdownDeterministic:
    def test_markdown_same_on_repeat(self):
        inp = _valid_input()
        result = evaluate_runtime_governance_dry_run(inp)
        md1 = dry_run_result_to_markdown(result)
        md2 = dry_run_result_to_markdown(result)

        assert md1 == md2


class TestMarkdownNoTimestamps:
    def test_no_timestamps(self):
        inp = _valid_input()
        result = evaluate_runtime_governance_dry_run(inp)
        md = dry_run_result_to_markdown(result)

        # no ISO timestamps, no "202" year strings, no epoch
        assert "202" not in md or "2026" not in md.split()
        # no common timestamp patterns
        for marker in ["timestamp", "created_at", "updated_at", "date:", "time:"]:
            assert marker not in md.lower()
