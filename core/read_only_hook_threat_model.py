"""Read-only hook threat model — pure frozen dataclasses, no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

THREAT_IDS = [
    "T01_PERMISSION_ESCALATION",
    "T02_SECRET_LEAKAGE",
    "T03_SIDE_EFFECT_INJECTION",
    "T04_INVARIANT_BYPASS",
    "T05_OUTPUT_TAMPERING",
]


@dataclass(frozen=True)
class ThreatModelItem:
    threat_id: str
    title: str
    severity: str
    mitigation: str
    status: str  # "mitigated", "accepted", "open"


def build_default_threat_model() -> List[ThreatModelItem]:
    return [
        ThreatModelItem(
            threat_id="T01_PERMISSION_ESCALATION",
            title="Attacker gains write/execute permission via hook",
            severity="CRITICAL",
            mitigation="Hard-coded DENIED_PERMISSIONS set; check_permission rejects unknowns",
            status="mitigated",
        ),
        ThreatModelItem(
            threat_id="T02_SECRET_LEAKAGE",
            title="Secret values appear in sanitized output",
            severity="HIGH",
            mitigation="SECRET_PATTERNS scan on all payload keys; redacted before output",
            status="mitigated",
        ),
        ThreatModelItem(
            threat_id="T03_SIDE_EFFECT_INJECTION",
            title="Hook output declares non-empty side effects",
            severity="HIGH",
            mitigation="build_read_only_hook_output raises on non-empty side_effects_declared",
            status="mitigated",
        ),
        ThreatModelItem(
            threat_id="T04_INVARIANT_BYPASS",
            title="Context manipulation bypasses invariant checks",
            severity="MEDIUM",
            mitigation="Five independent invariant checks; all must pass for success",
            status="mitigated",
        ),
        ThreatModelItem(
            threat_id="T05_OUTPUT_TAMPERING",
            title="Mutable output dict modified after construction",
            severity="MEDIUM",
            mitigation="Frozen dataclasses; serializers return fresh copies",
            status="mitigated",
        ),
    ]


def threat_model_item_to_dict(item: ThreatModelItem) -> dict:
    return {
        "threat_id": item.threat_id,
        "title": item.title,
        "severity": item.severity,
        "mitigation": item.mitigation,
        "status": item.status,
    }
