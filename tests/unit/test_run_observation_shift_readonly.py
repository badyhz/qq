import json
import tempfile
from pathlib import Path

from scripts.run_observation_shift import (
    build_observation_shift_summary,
    render_observation_shift_markdown,
    run_observation_shift,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_readonly_summary_and_markdown_from_precomputed_state() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        state_jsonl = root / "state.jsonl"
        risk_jsonl = root / "risk.jsonl"
        candidates_jsonl = root / "candidates.jsonl"

        _write_jsonl(
            state_jsonl,
            [
                {
                    "symbol": "FETUSDT",
                    "positionAmt": 1.2,
                    "entryPrice": 0.5,
                    "markPrice": 0.6,
                    "open_stop_market_count": 1,
                    "open_take_profit_market_count": 1,
                    "protection_status": "FULLY_PROTECTED",
                    "action_required": "",
                },
                {
                    "symbol": "OPUSDT",
                    "positionAmt": 0.0,
                    "entryPrice": 0.0,
                    "markPrice": 0.0,
                    "open_stop_market_count": 0,
                    "open_take_profit_market_count": 0,
                    "protection_status": "FLAT_CLEAN",
                    "action_required": "",
                },
            ],
        )
        _write_jsonl(
            risk_jsonl,
            [
                {
                    "ts_utc": "2099-01-01T00:00:00Z",
                    "severity": "warn",
                    "event_type": "TEST_EVENT",
                    "symbol": "FETUSDT",
                    "message": "test",
                }
            ],
        )
        _write_jsonl(
            candidates_jsonl,
            [
                {"candidate_id": "c1", "status": "PENDING"},
                {"candidate_id": "c2", "status": "APPROVED"},
                {"candidate_id": "c3", "status": "SUBMITTED"},
            ],
        )

        summary = build_observation_shift_summary(
            env="testnet",
            symbols="FETUSDT,OPUSDT",
            shift_id="shift_test",
            state_jsonl=str(state_jsonl),
            risk_events_jsonl=str(risk_jsonl),
            candidates_jsonl=str(candidates_jsonl),
            lookback_minutes=60 * 24 * 365 * 200,
            dry_run=True,
        )

        assert summary["shift_id"] == "shift_test"
        assert summary["execution_candidates"]["total"] == 3
        assert summary["execution_candidates"]["pending"] == 1
        assert summary["execution_candidates"]["approved"] == 1
        assert summary["execution_candidates"]["submitted"] == 1
        assert len(summary["per_symbol_state"]) == 2
        assert "review_candidates" in summary["recommended_actions"]

        markdown = render_observation_shift_markdown(summary)
        assert "# Observation Shift Summary" in markdown
        assert "## Per Symbol State" in markdown
        assert "## Risk Events" in markdown
        assert "## Execution Candidates" in markdown
        assert "## Recommended Actions" in markdown

        output = run_observation_shift(
            env="testnet",
            symbols="FETUSDT,OPUSDT",
            shift_id="shift_test_write",
            state_jsonl=str(state_jsonl),
            risk_events_jsonl=str(risk_jsonl),
            candidates_jsonl=str(candidates_jsonl),
            output_dir=str(root / "out"),
            dry_run=True,
            lookback_minutes=60 * 24 * 365 * 200,
        )
        assert Path(output["summary_json"]).exists()
        assert Path(output["summary_md"]).exists()


def test_missing_state_jsonl_falls_back_to_preflight_unavailable() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        risk_jsonl = root / "risk.jsonl"
        candidates_jsonl = root / "candidates.jsonl"
        _write_jsonl(risk_jsonl, [])
        _write_jsonl(candidates_jsonl, [])

        summary = build_observation_shift_summary(
            env="testnet",
            symbols="FETUSDT",
            shift_id="shift_missing_state",
            state_jsonl="",
            risk_events_jsonl=str(risk_jsonl),
            candidates_jsonl=str(candidates_jsonl),
            dry_run=True,
        )

        row = summary["per_symbol_state"][0]
        assert row["protection_status"] == "preflight_unavailable"
        assert row["error_code"] == "readonly_state_missing"


def test_no_check_testnet_state_reference_in_readonly_module() -> None:
    module_path = Path(__file__).parent.parent.parent / "scripts" / "run_observation_shift.py"
    content = module_path.read_text(encoding="utf-8")
    assert "check_testnet_state" not in content
