from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumRiskCommandSafety:
    """T1215 - frozen dataclass for command safety rules."""

    rule_id: str
    pattern: str
    severity: str
    description: str


COMMAND_SAFETY_RULES: tuple[MediumRiskCommandSafety, ...] = (
    MediumRiskCommandSafety(
        rule_id="CS001",
        pattern="shell=True",
        severity="HIGH",
        description="subprocess must not use shell=True",
    ),
    MediumRiskCommandSafety(
        rule_id="CS002",
        pattern="eval(",
        severity="HIGH",
        description="eval() is forbidden in medium-risk scripts",
    ),
    MediumRiskCommandSafety(
        rule_id="CS003",
        pattern="exec(",
        severity="HIGH",
        description="exec() is forbidden in medium-risk scripts",
    ),
    MediumRiskCommandSafety(
        rule_id="CS004",
        pattern="importlib.import_module",
        severity="MEDIUM",
        description="dynamic import is forbidden in medium-risk scripts",
    ),
    MediumRiskCommandSafety(
        rule_id="CS005",
        pattern="__import__",
        severity="MEDIUM",
        description="__import__() is forbidden in medium-risk scripts",
    ),
)
