"""Governance policy for real adapter usage.

Enforces safety rules BEFORE any real API adapter connects:
- Allowlist gating
- Budget ceilings
- Rate limits
- Kill switch
- Credential isolation
- Endpoint declaration
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class AdapterPolicyViolation:
    rule: str
    severity: str
    detail: str


@dataclass
class AdapterPolicyResult:
    allowed: bool
    violations: list[AdapterPolicyViolation] = field(default_factory=list)


@dataclass
class BudgetCheckResult:
    within_budget: bool
    current_cost: float
    request_cost: float
    ceiling: float


class RealAdapterPolicy:
    """Pre-connection governance for real API adapters."""

    DEFAULT_BUDGET_CEILING = 10.00
    DEFAULT_RATE_LIMIT = 10  # requests per minute

    def __init__(self) -> None:
        self._allowlist: set[str] = set()
        self._kill_switch_active: bool = False
        self._killed_adapters: set[str] = set()
        self._budget_ceilings: dict[str, float] = {}
        self._costs: dict[str, float] = {}
        self._rate_windows: dict[str, list[float]] = {}
        self._configs: dict[str, dict] = {}
        self._registered: set[str] = set()

    # -- registration validation --

    def validate_adapter_registration(
        self, adapter_id: str, config: dict
    ) -> AdapterPolicyResult:
        violations: list[AdapterPolicyViolation] = []

        if not adapter_id or not isinstance(adapter_id, str):
            violations.append(
                AdapterPolicyViolation(
                    rule="adapter_id_required",
                    severity="critical",
                    detail="adapter_id must be a non-empty string",
                )
            )

        if not config or not isinstance(config, dict):
            violations.append(
                AdapterPolicyViolation(
                    rule="config_required",
                    severity="critical",
                    detail="config must be a non-empty dict",
                )
            )
            return AdapterPolicyResult(allowed=False, violations=violations)

        # credential isolation: config must not contain cross-adapter references
        cross_refs = config.get("cross_adapter_refs", {})
        if cross_refs:
            violations.append(
                AdapterPolicyViolation(
                    rule="credential_isolation",
                    severity="critical",
                    detail=f"adapter {adapter_id} references other adapters' credentials: {list(cross_refs.keys())}",
                )
            )

        # network policy: endpoint must be declared
        if not config.get("endpoint"):
            violations.append(
                AdapterPolicyViolation(
                    rule="endpoint_required",
                    severity="critical",
                    detail="adapter must declare its endpoint (even sandbox)",
                )
            )

        allowed = len(violations) == 0
        return AdapterPolicyResult(allowed=allowed, violations=violations)

    # -- request validation --

    def validate_request(
        self, adapter_id: str, request: dict
    ) -> AdapterPolicyResult:
        violations: list[AdapterPolicyViolation] = []

        if self._kill_switch_active:
            violations.append(
                AdapterPolicyViolation(
                    rule="kill_switch_global",
                    severity="critical",
                    detail="global kill switch is active",
                )
            )
            return AdapterPolicyResult(allowed=False, violations=violations)

        if adapter_id in self._killed_adapters:
            violations.append(
                AdapterPolicyViolation(
                    rule="kill_switch_adapter",
                    severity="critical",
                    detail=f"adapter {adapter_id} is killed",
                )
            )
            return AdapterPolicyResult(allowed=False, violations=violations)

        if adapter_id not in self._registered:
            violations.append(
                AdapterPolicyViolation(
                    rule="not_registered",
                    severity="critical",
                    detail=f"adapter {adapter_id} is not registered",
                )
            )

        if not self.is_allowed(adapter_id):
            violations.append(
                AdapterPolicyViolation(
                    rule="not_on_allowlist",
                    severity="critical",
                    detail=f"adapter {adapter_id} is not on the allowlist",
                )
            )

        # credential isolation at request level
        if request.get("access_other_adapter_config"):
            violations.append(
                AdapterPolicyViolation(
                    rule="credential_isolation",
                    severity="critical",
                    detail=f"adapter {adapter_id} attempted to access another adapter's config",
                )
            )

        allowed = len(violations) == 0
        return AdapterPolicyResult(allowed=allowed, violations=violations)

    # -- budget --

    def check_budget_ceiling(
        self,
        adapter_id: str,
        current_cost_usd: float,
        request_cost_usd: float,
    ) -> BudgetCheckResult:
        ceiling = self._budget_ceilings.get(adapter_id, self.DEFAULT_BUDGET_CEILING)
        projected = current_cost_usd + request_cost_usd
        within = projected <= ceiling
        self._costs[adapter_id] = projected if within else current_cost_usd
        return BudgetCheckResult(
            within_budget=within,
            current_cost=current_cost_usd,
            request_cost=request_cost_usd,
            ceiling=ceiling,
        )

    # -- rate limit --

    def check_rate_limit(self, adapter_id: str) -> bool:
        now = time.time()
        window = self._rate_windows.setdefault(adapter_id, [])
        # prune entries older than 60s
        self._rate_windows[adapter_id] = [t for t in window if now - t < 60]
        if len(self._rate_windows[adapter_id]) >= self.DEFAULT_RATE_LIMIT:
            return False
        self._rate_windows[adapter_id].append(now)
        return True

    # -- kill switch --

    def activate_kill_switch(self, adapter_id: str | None = None) -> None:
        if adapter_id is None:
            self._kill_switch_active = True
        else:
            self._killed_adapters.add(adapter_id)

    def deactivate_kill_switch(self, adapter_id: str | None = None) -> None:
        if adapter_id is None:
            self._kill_switch_active = False
            self._killed_adapters.clear()
        else:
            self._killed_adapters.discard(adapter_id)

    def is_kill_switch_active(self, adapter_id: str) -> bool:
        if self._kill_switch_active:
            return True
        return adapter_id in self._killed_adapters

    # -- allowlist --

    def add_to_allowlist(self, adapter_id: str) -> None:
        self._allowlist.add(adapter_id)

    def remove_from_allowlist(self, adapter_id: str) -> None:
        self._allowlist.discard(adapter_id)

    def is_allowed(self, adapter_id: str) -> bool:
        return adapter_id in self._allowlist

    # -- registration helper --

    def register(self, adapter_id: str, config: dict) -> AdapterPolicyResult:
        result = self.validate_adapter_registration(adapter_id, config)
        if result.allowed:
            self._registered.add(adapter_id)
            self._configs[adapter_id] = dict(config)
        return result

    # -- credential isolation check --

    def get_adapter_config(self, adapter_id: str) -> dict | None:
        """Return config for the requesting adapter only."""
        return self._configs.get(adapter_id)

    # -- summary --

    def summary(self) -> dict:
        return {
            "registered": sorted(self._registered),
            "allowlist": sorted(self._allowlist),
            "kill_switch_global": self._kill_switch_active,
            "killed_adapters": sorted(self._killed_adapters),
            "budget_ceilings": dict(self._budget_ceilings),
            "costs": dict(self._costs),
            "default_budget_ceiling": self.DEFAULT_BUDGET_CEILING,
            "default_rate_limit": self.DEFAULT_RATE_LIMIT,
        }
