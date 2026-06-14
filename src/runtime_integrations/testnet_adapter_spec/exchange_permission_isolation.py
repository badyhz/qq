"""Exchange account and permission isolation plan."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class PermissionItem:
    perm_id: str
    title: str
    content: str
    required: bool
    def to_dict(self) -> dict:
        return {"perm_id": self.perm_id, "title": self.title, "content": self.content, "required": self.required}

PERMISSIONS = (
    PermissionItem("testnet_only", "Testnet-Only Account", "All operations restricted to testnet.binance.vision. No production access.", True),
    PermissionItem("subaccount_isolation", "Sub-Account Isolation", "Dedicated sub-account for automated trading. No shared accounts.", True),
    PermissionItem("ip_allowlist", "IP Allowlist Requirement", "API keys restricted to known IP addresses. No wildcard IPs.", True),
    PermissionItem("read_perm", "Read Permission", "Required for balance, position, and order status queries.", True),
    PermissionItem("order_create", "Order Create Permission", "Required for order submission. Scoped to allowed symbols only.", True),
    PermissionItem("order_cancel", "Order Cancel Permission", "Required for order cancellation. Must be idempotent.", True),
    PermissionItem("balance_read", "Balance Read Permission", "Required for account balance queries. Read-only.", True),
    PermissionItem("position_read", "Position Read Permission", "Required for position queries. Read-only.", True),
    PermissionItem("no_withdraw", "Withdraw Permission Forbidden", "Withdraw permission must not be granted. Any key with withdraw must be revoked.", True),
    PermissionItem("no_margin", "Margin/Borrow Forbidden", "Margin and borrow permissions forbidden unless explicitly approved by risk review.", True),
    PermissionItem("symbol_allowlist", "Symbol Allowlist", "Only approved symbols allowed. Default: empty (no symbols).", True),
    PermissionItem("notional_cap", "Notional Cap", "Per-order notional cap. Default: 0 (no orders). Requires explicit approval to increase.", True),
    PermissionItem("daily_order_cap", "Daily Order Cap", "Maximum orders per day. Default: 0. Requires explicit approval to increase.", True),
    PermissionItem("manual_freeze", "Manual Freeze Procedure", "Operator can freeze all trading immediately. Freeze requires manual unfreeze.", True),
)

def get_permissions() -> tuple[PermissionItem, ...]:
    return PERMISSIONS

def write_plan(permissions: tuple[PermissionItem, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([p.to_dict() for p in permissions], indent=2), encoding="utf-8")

def render_report(permissions: tuple[PermissionItem, ...]) -> str:
    lines = ["# Exchange Account and Permission Isolation Plan", "",
        "**Status: EXCHANGE_PERMISSION_ISOLATION_PLAN_READY**",
        "**Submit: TESTNET_SUBMIT_NOT_ALLOWED**", ""]
    for p in permissions:
        lines.extend([f"## {p.title}", "", p.content, ""])
    lines.extend(["## Conclusion", "", "EXCHANGE_PERMISSION_ISOLATION_PLAN_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
