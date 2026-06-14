"""Exchange capability inventory."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class CapabilityEntry:
    capability_id: str
    capability_name: str
    access_mode: str
    required_permission: str
    allowed_in_current_stage: bool
    prohibited_reason: str
    evidence_required: str
    final_status: str
    def to_dict(self) -> dict:
        return {
            "capability_id": self.capability_id, "capability_name": self.capability_name,
            "access_mode": self.access_mode, "required_permission": self.required_permission,
            "allowed_in_current_stage": self.allowed_in_current_stage,
            "prohibited_reason": self.prohibited_reason,
            "evidence_required": self.evidence_required, "final_status": self.final_status,
        }


@dataclass(frozen=True)
class CapabilityInventory:
    inventory_id: str
    created_at: str
    exchange_name: str
    capabilities: tuple[CapabilityEntry, ...]
    def to_dict(self) -> dict:
        return {"inventory_id": self.inventory_id, "created_at": self.created_at,
                "exchange_name": self.exchange_name,
                "capabilities": [c.to_dict() for c in self.capabilities]}


CAPABILITIES = (
    CapabilityEntry("CAP_001", "exchange_metadata", "MOCK_ONLY", "NONE", True, "", "Mock data sufficient", "AVAILABLE_MOCK"),
    CapabilityEntry("CAP_002", "account_metadata", "READ_ONLY_CANDIDATE", "READ_ONLY_TESTNET", True, "", "Read-only testnet permission required", "DESIGN_ONLY"),
    CapabilityEntry("CAP_003", "symbol_rules", "READ_ONLY_CANDIDATE", "MARKET_DATA_READ", True, "", "Market data read permission required", "DESIGN_ONLY"),
    CapabilityEntry("CAP_004", "rate_limits", "READ_ONLY_CANDIDATE", "NONE", True, "", "Public endpoint, no auth required", "DESIGN_ONLY"),
    CapabilityEntry("CAP_005", "server_time", "READ_ONLY_CANDIDATE", "NONE", True, "", "Public endpoint, no auth required", "DESIGN_ONLY"),
    CapabilityEntry("CAP_006", "order_submit", "DESIGN_ONLY", "TRADE_WRITE", False, "Submit prohibited in current stage", "Submit approval required", "PROHIBITED"),
    CapabilityEntry("CAP_007", "order_cancel", "DESIGN_ONLY", "TRADE_WRITE", False, "Cancel prohibited in current stage", "Cancel safety validation required", "PROHIBITED"),
    CapabilityEntry("CAP_008", "balance_reconciliation", "DESIGN_ONLY", "READ_ONLY_TESTNET", False, "Reconciliation locked until submit validated", "Reconciliation approval required", "PROHIBITED"),
    CapabilityEntry("CAP_009", "position_reconciliation", "DESIGN_ONLY", "READ_ONLY_TESTNET", False, "Reconciliation locked until submit validated", "Reconciliation approval required", "PROHIBITED"),
    CapabilityEntry("CAP_010", "withdrawal", "DESIGN_ONLY", "WITHDRAWAL_WRITE", False, "Withdrawal permanently prohibited", "Never allowed in automated system", "PROHIBITED"),
)


def create_inventory() -> CapabilityInventory:
    return CapabilityInventory(
        inventory_id=f"INV_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        exchange_name="BINANCE_PLACEHOLDER",
        capabilities=CAPABILITIES,
    )


def count_allowed(inventory: CapabilityInventory) -> int:
    return sum(1 for c in inventory.capabilities if c.allowed_in_current_stage)


def count_prohibited(inventory: CapabilityInventory) -> int:
    return sum(1 for c in inventory.capabilities if not c.allowed_in_current_stage)


def write_inventory(inventory: CapabilityInventory, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(inventory.to_dict(), indent=2), encoding="utf-8")


def render_report(inventory: CapabilityInventory) -> str:
    lines = ["# Exchange Capability Inventory", "",
        f"**inventory_id={inventory.inventory_id}**",
        f"**exchange={inventory.exchange_name}**",
        f"**allowed={count_allowed(inventory)}**",
        f"**prohibited={count_prohibited(inventory)}**",
        "**SUBMIT_CAPABILITY_PROHIBITED**", "",
        "## Capabilities", "",
        "| ID | Name | Access Mode | Allowed | Status |",
        "|----|------|-------------|---------|--------|"]
    for c in inventory.capabilities:
        allowed = "YES" if c.allowed_in_current_stage else "NO"
        lines.append(f"| {c.capability_id} | {c.capability_name} | {c.access_mode} | {allowed} | {c.final_status} |")
    lines.extend(["", "## Conclusion", "",
        "EXCHANGE_CAPABILITY_INVENTORY_READY",
        "SUBMIT_CAPABILITY_PROHIBITED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
