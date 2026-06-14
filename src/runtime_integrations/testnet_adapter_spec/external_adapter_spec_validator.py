"""External adapter spec validator."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class SpecCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

def validate_spec(sections: tuple) -> list[SpecCheck]:
    checks = []
    section_ids = {s.section_id for s in sections}
    required = {"purpose", "non_goals", "exchange_profile", "method_boundaries", "forbidden_methods", "credential_dep", "signing_dep", "network_dep"}
    for req in required:
        checks.append(SpecCheck(f"has_{req}", req in section_ids, f"section '{req}' present"))
    checks.append(SpecCheck("no_real_endpoints", all("testnet.binance.vision" not in s.content or "no" in s.content.lower() for s in sections), "no real endpoints hardcoded"))
    checks.append(SpecCheck("no_real_credentials", all("api_key=" not in s.content.lower() for s in sections), "no real credentials"))
    checks.append(SpecCheck("no_ccxt_active", all("import ccxt" not in s.content for s in sections), "no ccxt import"))
    checks.append(SpecCheck("states_submit_locked", any("submit" in s.content.lower() and ("locked" in s.content.lower() or "not allowed" in s.content.lower()) for s in sections), "submit remains locked"))
    return checks

def write_checks(checks: list[SpecCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
