from __future__ import annotations

from pathlib import Path

CS = Path("docs/dev_prd/runtime_governance_current_state.md")


def _read() -> str:
    return CS.read_text(encoding="utf-8")


def test_current_state_doc_exists() -> None:
    assert CS.exists(), f"Missing: {CS}"


def test_mentions_freeze_aware_governance() -> None:
    text = _read().lower()
    assert "freeze" in text or "freeze-aware" in text


def test_mentions_release_hold() -> None:
    text = _read()
    assert "HOLD" in text


def test_mentions_no_live_trading() -> None:
    text = _read().lower()
    assert "no live trading" in text or "not live trading" in text or "no live" in text
