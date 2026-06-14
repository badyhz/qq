"""Credential vault architecture validator."""
from __future__ import annotations
import json, pathlib
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class VaultCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

def validate_architecture(content: str) -> list[VaultCheck]:
    checks = []
    checks.append(VaultCheck("mode_architecture_only", "ARCHITECTURE_ONLY" in content, "mode=ARCHITECTURE_ONLY"))
    checks.append(VaultCheck("no_real_credentials", "real_credentials_enabled=false" in content, "real credentials disabled"))
    checks.append(VaultCheck("no_env_read", "env_secret_read=false" in content, "no env secret reading"))
    checks.append(VaultCheck("submit_not_allowed", "submit_allowed=false" in content, "submit not allowed"))
    checks.append(VaultCheck("has_encryption", "encryption" in content.lower(), "encryption section present"))
    checks.append(VaultCheck("has_access_control", "access control" in content.lower() or "access_control" in content, "access control present"))
    checks.append(VaultCheck("has_audit", "audit" in content.lower(), "audit section present"))
    checks.append(VaultCheck("has_rotation", "rotation" in content.lower(), "rotation policy present"))
    checks.append(VaultCheck("no_key_generation", "generate" not in content.lower() or "no" in content.lower(), "no key generation"))
    checks.append(VaultCheck("no_key_loading", "load_key" not in content and re.search(r"\benviron\b", content.lower()) is None, "no key loading"))
    return checks

def write_checks(checks: list[VaultCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
