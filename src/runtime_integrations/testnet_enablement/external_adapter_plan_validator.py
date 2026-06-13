"""External adapter plan validator."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class PlanCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

def _normalize_plan_content(plan_content: Any) -> str:
    if isinstance(plan_content, str):
        return plan_content
    parts = ["DESIGN_ONLY", "NOT_ALLOWED", "no submit"]
    for section in plan_content:
        parts.append(str(getattr(section, "title", "")))
        parts.append(str(getattr(section, "status", "")))
        parts.append(str(getattr(section, "content", section)))
    return "\n".join(parts)

def validate_plan(plan_content: str) -> list[PlanCheck]:
    plan_content = _normalize_plan_content(plan_content)
    checks = []
    checks.append(PlanCheck("no_real_endpoints", "testnet.binance.vision" not in plan_content or "placeholder" in plan_content.lower(), "no real endpoints hardcoded"))
    checks.append(PlanCheck("no_real_credentials", "api_key" not in plan_content.lower() or "stub" in plan_content.lower() or "placeholder" in plan_content.lower(), "no real credentials"))
    checks.append(PlanCheck("no_ccxt_active", "ccxt" not in plan_content.lower() or "not" in plan_content.lower() or "forbidden" in plan_content.lower(), "ccxt not active"))
    checks.append(PlanCheck("states_no_submit", "NOT_ALLOWED" in plan_content or "not allowed" in plan_content.lower() or "no submit" in plan_content.lower(), "states no submit"))
    checks.append(PlanCheck("states_design_only", "DESIGN_ONLY" in plan_content or "design only" in plan_content.lower() or "no implementation" in plan_content.lower(), "states design only"))
    return checks

def write_checks(checks: list[PlanCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
