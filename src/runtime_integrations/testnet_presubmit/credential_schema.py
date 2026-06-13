"""Credential schema for testnet pre-submit review."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class CredentialSchema:
    exchange_name: str
    account_scope: str  # SPOT, FUTURES, MARGIN
    key_label: str
    permissions_required: tuple[str, ...]
    permissions_forbidden: tuple[str, ...]
    rotation_required: bool
    redaction_required: bool
    human_review_required: bool
    def to_dict(self) -> dict:
        return {"exchange_name": self.exchange_name, "account_scope": self.account_scope, "key_label": self.key_label, "permissions_required": list(self.permissions_required), "permissions_forbidden": list(self.permissions_forbidden), "rotation_required": self.rotation_required, "redaction_required": self.redaction_required, "human_review_required": self.human_review_required}

DEFAULT_SCHEMAS = (
    CredentialSchema("binance", "SPOT", "testnet_spot_key", ("SPOT_READ", "SPOT_TRADE"), ("WITHDRAW", "TRANSFER"), True, True, True),
    CredentialSchema("binance", "FUTURES", "testnet_futures_key", ("FUTURES_READ", "FUTURES_TRADE"), ("WITHDRAW", "TRANSFER"), True, True, True),
)

def get_schemas() -> tuple[CredentialSchema, ...]:
    return DEFAULT_SCHEMAS

def write_schemas(schemas: tuple[CredentialSchema, ...], out) -> None:
    import json, pathlib
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([s.to_dict() for s in schemas], indent=2), encoding="utf-8")
