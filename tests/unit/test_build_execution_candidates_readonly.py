import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.build_execution_candidates import build_execution_candidates


def _write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _make_input_row(symbol="FETUSDT", quantity=0.1, notional=5.0, dry_run_id="test-001"):
    return {
        "symbol": symbol,
        "testnet_payload": {
            "symbol": symbol,
            "quantity": quantity,
            "notional_usdt": notional,
            "entry": {"price": "0.05"},
            "side": "BUY",
            "type": "MARKET",
            "stop_loss_plan": {"enabled": True},
            "take_profit_plan": {"enabled": True},
            "source_shadow_timestamp": "2026-01-01T00:00:00Z",
            "confidence": "high",
            "dry_run_id": dry_run_id,
        },
    }


def test_no_preflight_state_jsonl_creates_pending_with_preflight_skipped():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.jsonl")
        output_path = os.path.join(tmpdir, "output.jsonl")
        _write_jsonl(input_path, [_make_input_row("FETUSDT")])

        result = build_execution_candidates(
            env="testnet",
            input_jsonl=input_path,
            output_jsonl=output_path,
            symbols="FETUSDT",
            allowlist="FETUSDT",
            max_candidates=10,
            dry_run=True,
            preflight_state_jsonl="",
        )

        assert result["candidates_created"] == 1
        assert result["candidates_skipped"] == 0
        candidate = result["generated_candidates"][0]
        assert candidate["status"] == "PENDING"
        assert candidate["preflight_status"] == "PREFLIGHT_SKIPPED"
        assert "PREFLIGHT_SKIPPED" in candidate["risk_flags"]
        assert "no preflight check" in candidate["reason"]


def test_preflight_state_fully_protected_skips_candidate():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.jsonl")
        output_path = os.path.join(tmpdir, "output.jsonl")
        state_path = os.path.join(tmpdir, "state.jsonl")
        _write_jsonl(input_path, [_make_input_row("FETUSDT")])
        _write_jsonl(state_path, [{"symbol": "FETUSDT", "ok": True, "protection_status": "FULLY_PROTECTED"}])

        result = build_execution_candidates(
            env="testnet",
            input_jsonl=input_path,
            output_jsonl=output_path,
            symbols="FETUSDT",
            allowlist="FETUSDT",
            max_candidates=10,
            dry_run=True,
            preflight_state_jsonl=state_path,
        )

        assert result["candidates_created"] == 0
        assert result["candidates_skipped"] == 1
        assert "already_fully_protected" in result["skipped_reasons"]


def test_preflight_state_naked_position_skips_candidate():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.jsonl")
        output_path = os.path.join(tmpdir, "output.jsonl")
        state_path = os.path.join(tmpdir, "state.jsonl")
        _write_jsonl(input_path, [_make_input_row("FETUSDT")])
        _write_jsonl(state_path, [{"symbol": "FETUSDT", "ok": True, "protection_status": "NAKED_POSITION"}])

        result = build_execution_candidates(
            env="testnet",
            input_jsonl=input_path,
            output_jsonl=output_path,
            symbols="FETUSDT",
            allowlist="FETUSDT",
            max_candidates=10,
            dry_run=True,
            preflight_state_jsonl=state_path,
        )

        assert result["candidates_created"] == 0
        assert result["candidates_skipped"] == 1
        assert "naked_position_detected" in result["skipped_reasons"]


def test_preflight_state_orphan_protection_skips_candidate():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.jsonl")
        output_path = os.path.join(tmpdir, "output.jsonl")
        state_path = os.path.join(tmpdir, "state.jsonl")
        _write_jsonl(input_path, [_make_input_row("FETUSDT")])
        _write_jsonl(state_path, [{"symbol": "FETUSDT", "ok": True, "protection_status": "ORPHAN_PROTECTION"}])

        result = build_execution_candidates(
            env="testnet",
            input_jsonl=input_path,
            output_jsonl=output_path,
            symbols="FETUSDT",
            allowlist="FETUSDT",
            max_candidates=10,
            dry_run=True,
            preflight_state_jsonl=state_path,
        )

        assert result["candidates_created"] == 0
        assert result["candidates_skipped"] == 1
        assert "orphan_protection_detected" in result["skipped_reasons"]


def test_preflight_state_partial_protected_skips_candidate():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.jsonl")
        output_path = os.path.join(tmpdir, "output.jsonl")
        state_path = os.path.join(tmpdir, "state.jsonl")
        _write_jsonl(input_path, [_make_input_row("FETUSDT")])
        _write_jsonl(state_path, [{"symbol": "FETUSDT", "ok": True, "protection_status": "PARTIAL_PROTECTED"}])

        result = build_execution_candidates(
            env="testnet",
            input_jsonl=input_path,
            output_jsonl=output_path,
            symbols="FETUSDT",
            allowlist="FETUSDT",
            max_candidates=10,
            dry_run=True,
            preflight_state_jsonl=state_path,
        )

        assert result["candidates_created"] == 0
        assert result["candidates_skipped"] == 1
        assert "partial_protection_detected" in result["skipped_reasons"]


def test_missing_symbol_in_state_jsonl_skips_with_preflight_unavailable():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.jsonl")
        output_path = os.path.join(tmpdir, "output.jsonl")
        state_path = os.path.join(tmpdir, "state.jsonl")
        _write_jsonl(input_path, [_make_input_row("FETUSDT")])
        _write_jsonl(state_path, [{"symbol": "OPUSDT", "ok": True, "protection_status": "FULLY_PROTECTED"}])

        result = build_execution_candidates(
            env="testnet",
            input_jsonl=input_path,
            output_jsonl=output_path,
            symbols="FETUSDT",
            allowlist="FETUSDT",
            max_candidates=10,
            dry_run=True,
            preflight_state_jsonl=state_path,
        )

        assert result["candidates_created"] == 0
        assert result["candidates_skipped"] == 1
        assert "preflight_unavailable" in result["skipped_reasons"]


def test_state_jsonl_ok_false_skips_with_preflight_unavailable():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.jsonl")
        output_path = os.path.join(tmpdir, "output.jsonl")
        state_path = os.path.join(tmpdir, "state.jsonl")
        _write_jsonl(input_path, [_make_input_row("FETUSDT")])
        _write_jsonl(state_path, [{"symbol": "FETUSDT", "ok": False, "protection_status": ""}])

        result = build_execution_candidates(
            env="testnet",
            input_jsonl=input_path,
            output_jsonl=output_path,
            symbols="FETUSDT",
            allowlist="FETUSDT",
            max_candidates=10,
            dry_run=True,
            preflight_state_jsonl=state_path,
        )

        assert result["candidates_created"] == 0
        assert result["candidates_skipped"] == 1
        assert "preflight_unavailable" in result["skipped_reasons"]


def test_state_jsonl_file_missing_behaves_like_no_input():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.jsonl")
        output_path = os.path.join(tmpdir, "output.jsonl")
        _write_jsonl(input_path, [_make_input_row("FETUSDT")])

        result = build_execution_candidates(
            env="testnet",
            input_jsonl=input_path,
            output_jsonl=output_path,
            symbols="FETUSDT",
            allowlist="FETUSDT",
            max_candidates=10,
            dry_run=True,
            preflight_state_jsonl=os.path.join(tmpdir, "nonexistent.jsonl"),
        )

        assert result["candidates_created"] == 1
        candidate = result["generated_candidates"][0]
        assert candidate["status"] == "PENDING"
        assert candidate["preflight_status"] == "PREFLIGHT_SKIPPED"
        assert "PREFLIGHT_SKIPPED" in candidate["risk_flags"]


def test_no_check_testnet_state_import():
    script_path = Path(__file__).parent.parent.parent / "scripts" / "build_execution_candidates.py"
    content = script_path.read_text(encoding="utf-8")
    assert "check_testnet_state" not in content
