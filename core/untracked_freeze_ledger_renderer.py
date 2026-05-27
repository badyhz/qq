from __future__ import annotations

from core.untracked_freeze_ledger import UntrackedFreezeLedger
from core.untracked_file_state import UntrackedFileState
from core.untracked_risk_class import UntrackedRiskClass
from core.untracked_freeze_ledger_verdict import UntrackedFreezeLedgerVerdict


def render_untracked_freeze_ledger_md(ledger: UntrackedFreezeLedger) -> str:
    """Render an UntrackedFreezeLedger as markdown."""
    lines = ("# Untracked Freeze Ledger", "")
    lines += (f"- **Ledger ID:** {ledger.ledger_id}",)
    lines += (f"- **Entries:** {len(ledger.entries)}",)
    lines += (f"- **Frozen files:** {ledger.frozen_count()}",)
    lines += (f"- **Release hold:** {ledger.has_release_hold()}",)
    lines += ("",)
    if ledger.frozen_files:
        lines += ("## Frozen Files",)
        for f in ledger.frozen_files:
            lines += (f"- {f}",)
        lines += ("",)
    if ledger.entries:
        lines += ("## Entries",)
        for entry in ledger.entries:
            path = getattr(entry, "file_path", getattr(entry, "path", str(entry)))
            lines += (f"- {path}",)
        lines += ("",)
    return "\n".join(lines)


def render_untracked_file_state_md(state: UntrackedFileState) -> str:
    """Render an UntrackedFileState as markdown."""
    lines = ("# Untracked File State", "")
    lines += (f"- **Value:** {state.value}",)
    lines += (f"- **Valid states:** {', '.join(UntrackedFileState.ALL_STATES)}",)
    return "\n".join(lines)


def render_untracked_risk_class_md(risk: UntrackedRiskClass) -> str:
    """Render an UntrackedRiskClass as markdown."""
    lines = ("# Untracked Risk Class", "")
    lines += (f"- **Value:** {risk.value}",)
    lines += (f"- **Valid classes:** {', '.join(UntrackedRiskClass.ALL_CLASSES)}",)
    return "\n".join(lines)


def render_untracked_ledger_verdict_md(verdict: UntrackedFreezeLedgerVerdict) -> str:
    """Render an UntrackedFreezeLedgerVerdict as markdown."""
    lines = ("# Untracked Freeze Ledger Verdict", "")
    lines += (f"- **Verdict:** {verdict.verdict}",)
    lines += (f"- **High risk count:** {verdict.high_risk_count}",)
    lines += (f"- **Medium risk count:** {verdict.medium_risk_count}",)
    lines += (f"- **Low risk count:** {verdict.low_risk_count}",)
    lines += (f"- **Total risk count:** {verdict.total_risk_count()}",)
    if verdict.notes:
        lines += (f"- **Notes:** {verdict.notes}",)
    return "\n".join(lines)
