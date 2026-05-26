"""Adapter Preflight Validator — checks ALL safety layers before real adapter invocation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class PreflightStatus(Enum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"


@dataclass
class PreflightCheck:
    name: str
    passed: bool
    detail: str


@dataclass
class PreflightResult:
    status: PreflightStatus
    checks: list[PreflightCheck] = field(default_factory=list)
    timestamp: float = 0.0


class AdapterPreflightValidator:
    """Validates ALL safety layers before any real adapter invocation."""

    def __init__(
        self,
        credential_manager=None,
        network_sandbox=None,
        real_adapter_policy=None,
        approval_gate=None,
        capability_registry=None,
    ) -> None:
        self.credential_manager = credential_manager
        self.network_sandbox = network_sandbox
        self.real_adapter_policy = real_adapter_policy
        self.approval_gate = approval_gate
        self.capability_registry = capability_registry
        self._custom_checks: dict[str, Callable] = {}

    def validate(self, adapter_id: str, action: str = "default") -> PreflightResult:
        """Run all preflight checks in order."""
        checks: list[PreflightCheck] = []

        # 1. Credential check
        if self.credential_manager is not None:
            has_cred = self.credential_manager.has_credential(adapter_id)
            checks.append(PreflightCheck(
                name="credential",
                passed=has_cred,
                detail="credential available" if has_cred else f"no credential for {adapter_id}",
            ))
        else:
            checks.append(PreflightCheck(
                name="credential",
                passed=True,
                detail="skipped: no credential_manager",
            ))

        # 2. Network check
        if self.network_sandbox is not None:
            not_offline = self.network_sandbox._mode != "offline"
            checks.append(PreflightCheck(
                name="network",
                passed=not_offline,
                detail="network available" if not_offline else "network is in offline mode",
            ))
        else:
            checks.append(PreflightCheck(
                name="network",
                passed=True,
                detail="skipped: no network_sandbox",
            ))

        # 3. Budget / allowlist check
        if self.real_adapter_policy is not None:
            on_allowlist = self.real_adapter_policy.is_allowed(adapter_id)
            checks.append(PreflightCheck(
                name="budget",
                passed=on_allowlist,
                detail="adapter on allowlist" if on_allowlist else f"{adapter_id} not on allowlist",
            ))
        else:
            checks.append(PreflightCheck(
                name="budget",
                passed=True,
                detail="skipped: no real_adapter_policy",
            ))

        # 4. Capability check
        if self.capability_registry is not None:
            from core.live_capability_registry import LiveCapability
            allowed = self.capability_registry.is_allowed(LiveCapability.LIVE_EXECUTION, adapter_id)
            checks.append(PreflightCheck(
                name="capability",
                passed=allowed,
                detail="capability registered" if allowed else f"LIVE_EXECUTION not allowed for {adapter_id}",
            ))
        else:
            checks.append(PreflightCheck(
                name="capability",
                passed=True,
                detail="skipped: no capability_registry",
            ))

        # 5. Approval check
        if self.approval_gate is not None:
            approved = self.approval_gate.is_approved(action, adapter_id)
            checks.append(PreflightCheck(
                name="approval",
                passed=approved,
                detail="approval found" if approved else f"no approval for {adapter_id}/{action}",
            ))
        else:
            checks.append(PreflightCheck(
                name="approval",
                passed=True,
                detail="skipped: no approval_gate",
            ))

        # 6. Custom checks
        for name, fn in self._custom_checks.items():
            try:
                passed = fn(adapter_id, action)
                checks.append(PreflightCheck(
                    name=name,
                    passed=passed,
                    detail="ok" if passed else f"custom check {name} failed",
                ))
            except Exception as exc:
                checks.append(PreflightCheck(
                    name=name,
                    passed=False,
                    detail=f"custom check {name} raised: {exc}",
                ))

        # Determine status
        has_failure = any(not c.passed for c in checks)
        if has_failure:
            status = PreflightStatus.FAIL
        else:
            has_skipped = any("skipped" in c.detail for c in checks)
            status = PreflightStatus.PARTIAL if has_skipped else PreflightStatus.PASS

        return PreflightResult(
            status=status,
            checks=checks,
            timestamp=time.time(),
        )

    def add_check(self, name: str, check_fn: Callable) -> None:
        """Add a custom preflight check."""
        self._custom_checks[name] = check_fn

    def remove_check(self, name: str) -> None:
        """Remove a custom preflight check."""
        self._custom_checks.pop(name, None)

    def summary(self) -> dict:
        """Validator state."""
        return {
            "credential_manager": self.credential_manager is not None,
            "network_sandbox": self.network_sandbox is not None,
            "real_adapter_policy": self.real_adapter_policy is not None,
            "approval_gate": self.approval_gate is not None,
            "capability_registry": self.capability_registry is not None,
            "custom_checks": list(self._custom_checks.keys()),
        }
