"""Exchange permission review checklist."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class PermissionItem:
    perm_id: str
    description: str
    required: bool
    status: str  # NOT_CONFIGURED, DESIGNED_ONLY, BLOCKED
    def to_dict(self) -> dict:
        return {"perm_id": self.perm_id, "description": self.description, "required": self.required, "status": self.status}

PERMISSIONS = (
    PermissionItem("perm_read", "Read permission for account data", True, "NOT_CONFIGURED"),
    PermissionItem("perm_trade", "Trade permission for order submission", True, "NOT_CONFIGURED"),
    PermissionItem("perm_no_withdraw", "Withdraw permission forbidden", True, "BLOCKED"),
    PermissionItem("perm_subaccount", "Sub-account isolation", True, "NOT_CONFIGURED"),
    PermissionItem("perm_ip_allowlist", "IP allowlist restriction", True, "NOT_CONFIGURED"),
    PermissionItem("perm_rate_limit_docs", "Rate limit documentation", True, "NOT_CONFIGURED"),
    PermissionItem("perm_testnet_only", "Testnet-only environment", True, "NOT_CONFIGURED"),
    PermissionItem("perm_kill_switch", "Kill switch compatibility", True, "DESIGNED_ONLY"),
    PermissionItem("perm_cancel", "Order cancel permission", True, "NOT_CONFIGURED"),
    PermissionItem("perm_balance_read", "Balance/position read permission", True, "NOT_CONFIGURED"),
    PermissionItem("perm_audit_export", "Audit export availability", True, "NOT_CONFIGURED"),
)

def get_permissions() -> tuple[PermissionItem, ...]:
    return PERMISSIONS

def write_permissions(perms: tuple[PermissionItem, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([p.to_dict() for p in perms], indent=2), encoding="utf-8")

def render_report(perms: tuple[PermissionItem, ...]) -> str:
    lines = ["# Exchange Permission Review Checklist", "", "**Status: EXCHANGE_PERMISSION_REVIEW_DOCUMENTED**", "**Submit: TESTNET_SUBMIT_NOT_ALLOWED**", "", "| Permission | Status |", "|------------|--------|"]
    for p in perms:
        lines.append(f"| {p.description} | {p.status} |")
    lines.extend(["", "## Conclusion", "", "EXCHANGE_PERMISSION_REVIEW_DOCUMENTED", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
