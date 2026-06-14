"""Vault stub validator."""
from __future__ import annotations
import json, pathlib, re
from dataclasses import dataclass

@dataclass(frozen=True)
class VaultCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

SUSPICIOUS_ENV_VARS = ("API_KEY", "API_SECRET", "BINANCE_API_KEY", "BINANCE_SECRET", "EXCHANGE_KEY", "EXCHANGE_SECRET", "TRADING_KEY", "TRADING_SECRET", "PRIVATE_KEY")

def validate_vault_stub(content: str) -> list[VaultCheck]:
    checks = []
    checks.append(VaultCheck("mode_stub_only", "STUB_ONLY" in content, "mode=STUB_ONLY"))
    checks.append(VaultCheck("no_real_credentials", "real_credentials_enabled=False" in content or "real_credentials_enabled=false" in content, "no real credentials"))
    checks.append(VaultCheck("no_env_read", "env_secret_read=False" in content or "env_secret_read=false" in content, "no env secret reading"))
    checks.append(VaultCheck("submit_not_allowed", "submit_allowed=False" in content or "submit_allowed=false" in content, "submit not allowed"))
    checks.append(VaultCheck("has_redacted", "redacted" in content.lower() or "****" in content, "redacted credentials"))
    checks.append(VaultCheck("has_placeholder", "placeholder" in content.lower() or "MOCK" in content, "placeholder credentials"))
    checks.append(VaultCheck("no_raw_api_key", not bool(re.search(r'[A-Za-z0-9]{32,64}', content)), "no raw API key"))
    checks.append(VaultCheck("no_suspicious_env", all(env not in content for env in SUSPICIOUS_ENV_VARS), "no suspicious env vars"))
    checks.append(VaultCheck("no_prod_reference", "production" not in content.lower() or "testnet" in content.lower() or "no" in content.lower(), "no production reference"))
    checks.append(VaultCheck("no_secret_string", "secret=" not in content.lower() and "api_key=" not in content.lower(), "no secret string"))
    return checks

def write_checks(checks: list[VaultCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
