import json
import tempfile
from pathlib import Path

from scripts.generate_notification_digest import build_digest


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_build_digest_local_inputs() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        risk_path = root / "risk.jsonl"
        cand_path = root / "cand.jsonl"
        summary_path = root / "summary.md"
        accept_path = root / "accept.md"

        _write_jsonl(
            risk_path,
            [
                {"severity": "warn", "event_type": "X", "message": "m1"},
                {"severity": "info", "event_type": "Y", "message": "m2"},
            ],
        )
        _write_jsonl(
            cand_path,
            [
                {"status": "PENDING"},
                {"status": "APPROVED"},
                {"status": "SUBMITTED"},
            ],
        )
        summary_path.write_text("summary", encoding="utf-8")
        accept_path.write_text("accept", encoding="utf-8")

        out = build_digest(
            env="testnet",
            title="Digest",
            summary_md=str(summary_path),
            risk_events_jsonl=str(risk_path),
            candidates_jsonl=str(cand_path),
            acceptance_report_md=str(accept_path),
            max_events=10,
        )

        assert "message" in out
        assert "## Candidates" in str(out["message"])
        assert "summary" in str(out["message"])
        assert out["candidates_summary"]["total"] == 3
        assert out["candidates_summary"]["pending"] == 1
        assert out["candidates_summary"]["approved"] == 1
        assert out["candidates_summary"]["submitted"] == 1
        assert out["severity_count"]["WARN"] == 1
        assert out["severity_count"]["INFO"] == 1
        assert out["truncated"] is False


def test_build_digest_truncates_long_text() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        summary_path = root / "summary.md"
        summary_path.write_text("A" * 6000, encoding="utf-8")

        out = build_digest(
            env="testnet",
            title="Digest",
            summary_md=str(summary_path),
            risk_events_jsonl="",
            candidates_jsonl="",
            acceptance_report_md="",
            max_events=0,
        )

        assert out["truncated"] is True
        assert "... [trim]" in str(out["message"])


def test_builder_has_no_send_side_effect_imports() -> None:
    path = Path(__file__).parent.parent.parent / "scripts" / "generate_notification_digest.py"
    content = path.read_text(encoding="utf-8")
    assert "send_notification" not in content
