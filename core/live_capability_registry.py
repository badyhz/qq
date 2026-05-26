"""Live Capability Registry.

Declares live permissions explicitly. Default: deny all.
Each adapter must register capabilities individually.
Deny always overrides registration.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LiveCapability(Enum):
    """Capabilities that can be granted to adapters."""

    NETWORK_CALL = "network_call"
    REAL_API = "real_api"
    REAL_CREDENTIAL = "real_credential"
    LIVE_EXECUTION = "live_execution"
    DATA_WRITE = "data_write"


@dataclass
class CapabilityRecord:
    """Record of a single capability registration."""

    capability: LiveCapability
    adapter_id: str
    registered: bool = False
    denied: bool = False
    requires_approval: bool = True


@dataclass
class CapabilityValidationResult:
    """Result of validating all adapters."""

    valid: bool
    denied: list[str] = field(default_factory=list)
    unregistered: list[str] = field(default_factory=list)
    approved: list[str] = field(default_factory=list)


class LiveCapabilityRegistry:
    """Registry for live capabilities per adapter.

    All capabilities denied by default.
    Must explicitly register each capability per adapter.
    Deny overrides registration (deny always wins).
    """

    def __init__(self) -> None:
        self._records: dict[tuple[LiveCapability, str], CapabilityRecord] = {}

    def _key(self, capability: LiveCapability, adapter_id: str) -> tuple[LiveCapability, str]:
        return (capability, adapter_id)

    def register_capability(
        self,
        capability: LiveCapability,
        adapter_id: str,
        requires_approval: bool = True,
    ) -> None:
        """Register that an adapter has a specific capability."""
        key = self._key(capability, adapter_id)
        if key in self._records:
            rec = self._records[key]
            rec.registered = True
            rec.requires_approval = requires_approval
        else:
            self._records[key] = CapabilityRecord(
                capability=capability,
                adapter_id=adapter_id,
                registered=True,
                denied=False,
                requires_approval=requires_approval,
            )

    def has_capability(self, capability: LiveCapability, adapter_id: str) -> bool:
        """Check if adapter has a registered capability."""
        key = self._key(capability, adapter_id)
        rec = self._records.get(key)
        return rec.registered if rec else False

    def is_allowed(self, capability: LiveCapability, adapter_id: str) -> bool:
        """Check if capability is allowed (registered AND not denied)."""
        key = self._key(capability, adapter_id)
        rec = self._records.get(key)
        if rec is None:
            return False
        return rec.registered and not rec.denied

    def deny_capability(self, capability: LiveCapability, adapter_id: str) -> None:
        """Explicitly deny a capability."""
        key = self._key(capability, adapter_id)
        if key in self._records:
            self._records[key].denied = True
        else:
            self._records[key] = CapabilityRecord(
                capability=capability,
                adapter_id=adapter_id,
                registered=False,
                denied=True,
            )

    def reinstate_capability(self, capability: LiveCapability, adapter_id: str) -> None:
        """Remove explicit deny from a capability."""
        key = self._key(capability, adapter_id)
        rec = self._records.get(key)
        if rec is not None:
            rec.denied = False

    def requires_approval(self, capability: LiveCapability, adapter_id: str) -> bool:
        """Check if capability requires manual approval."""
        key = self._key(capability, adapter_id)
        rec = self._records.get(key)
        if rec is None:
            return True
        return rec.requires_approval

    def list_capabilities(self, adapter_id: Optional[str] = None) -> dict:
        """List all capabilities, optionally filtered by adapter."""
        result: dict[str, dict[str, object]] = {}
        for (cap, aid), rec in self._records.items():
            if adapter_id is not None and aid != adapter_id:
                continue
            if aid not in result:
                result[aid] = {}
            result[aid][cap.value] = {
                "registered": rec.registered,
                "denied": rec.denied,
                "requires_approval": rec.requires_approval,
            }
        return result

    def validate_all(self, adapter_ids: list[str]) -> CapabilityValidationResult:
        """Validate all adapters have no unregistered capabilities."""
        denied: list[str] = []
        unregistered: list[str] = []
        approved: list[str] = []

        for aid in adapter_ids:
            has_any = False
            has_denied = False
            all_caps_registered = True

            for cap in LiveCapability:
                key = self._key(cap, aid)
                rec = self._records.get(key)
                if rec is None:
                    all_caps_registered = False
                    continue
                has_any = True
                if rec.denied:
                    has_denied = True
                if not rec.registered:
                    all_caps_registered = False

            if has_denied:
                denied.append(aid)
            elif not has_any or not all_caps_registered:
                unregistered.append(aid)
            else:
                approved.append(aid)

        valid = len(denied) == 0 and len(unregistered) == 0
        return CapabilityValidationResult(
            valid=valid,
            denied=denied,
            unregistered=unregistered,
            approved=approved,
        )

    def summary(self) -> dict:
        """Registry stats."""
        total = len(self._records)
        registered = sum(1 for r in self._records.values() if r.registered)
        denied = sum(1 for r in self._records.values() if r.denied)
        requires_approval = sum(
            1 for r in self._records.values() if r.requires_approval
        )
        adapters = len({r.adapter_id for r in self._records.values()})
        capabilities = len({r.capability for r in self._records.values()})

        return {
            "total_records": total,
            "registered": registered,
            "denied": denied,
            "requires_approval": requires_approval,
            "adapters": adapters,
            "capabilities": capabilities,
        }
