"""Feishu payload validator. Validates payloads without sending."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class PayloadValidation:
    payload_index: int
    valid: bool
    checks: tuple[str, ...]
    def to_dict(self) -> dict:
        return {"payload_index": self.payload_index, "valid": self.valid, "checks": list(self.checks)}

FORBIDDEN_FIELDS = ("webhook_url", "api_key", "secret", "token")
REQUIRED_FIELDS = ("dry_run", "actually_sent", "title", "severity")

def validate_payload(payload: dict, index: int) -> PayloadValidation:
    checks = []
    ok = True
    # dry_run must be True
    if payload.get("dry_run") is True:
        checks.append("dry_run=true")
    else:
        checks.append("DRY_RUN_NOT_TRUE"); ok = False
    # actually_sent must be False
    if payload.get("actually_sent") is False:
        checks.append("actually_sent=false")
    else:
        checks.append("ACTUALLY_SENT_NOT_FALSE"); ok = False
    # Required fields
    for f in REQUIRED_FIELDS:
        if f in payload:
            checks.append(f"required_present: {f}")
        else:
            checks.append(f"REQUIRED_MISSING: {f}"); ok = False
    # Forbidden fields
    for f in FORBIDDEN_FIELDS:
        if f in payload:
            checks.append(f"FORBIDDEN_FOUND: {f}"); ok = False
        else:
            checks.append(f"forbidden_absent: {f}")
    # No real webhook URL in feishu_card
    card = payload.get("feishu_card", {})
    card_str = json.dumps(card)
    if "https://open.feishu.cn" in card_str or "hooks.feishu.cn" in card_str:
        checks.append("REAL_WEBHOOK_IN_CARD"); ok = False
    else:
        checks.append("no_real_webhook_in_card")
    return PayloadValidation(index, ok, tuple(checks))

def validate_payloads_file(path: pathlib.Path) -> list[PayloadValidation]:
    if not path.exists():
        return []
    results = []
    for i, line in enumerate(path.read_text(encoding="utf-8").strip().splitlines()):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            results.append(validate_payload(payload, i))
        except json.JSONDecodeError:
            results.append(PayloadValidation(i, False, ("INVALID_JSON",)))
    return results

def write_validations(vals: list[PayloadValidation], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([v.to_dict() for v in vals], indent=2), encoding="utf-8")
