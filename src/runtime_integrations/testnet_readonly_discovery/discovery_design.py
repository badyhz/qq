"""Read-only testnet discovery design."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class DiscoveryDesign:
    discovery_id: str
    created_at: str
    exchange_name: str
    environment: str
    endpoint_class: str
    allowed_methods: tuple[str, ...]
    prohibited_methods: tuple[str, ...]
    required_permissions: tuple[str, ...]
    expected_response_schema: dict
    timeout_policy: str
    retry_policy: str
    audit_log_requirement: str
    final_decision: str
    def to_dict(self) -> dict:
        return {
            "discovery_id": self.discovery_id, "created_at": self.created_at,
            "exchange_name": self.exchange_name, "environment": self.environment,
            "endpoint_class": self.endpoint_class,
            "allowed_methods": list(self.allowed_methods),
            "prohibited_methods": list(self.prohibited_methods),
            "required_permissions": list(self.required_permissions),
            "expected_response_schema": self.expected_response_schema,
            "timeout_policy": self.timeout_policy, "retry_policy": self.retry_policy,
            "audit_log_requirement": self.audit_log_requirement,
            "final_decision": self.final_decision,
        }


ALLOWED_METHODS = (
    "GET_ACCOUNT_METADATA_DRY_RUN",
    "GET_EXCHANGE_INFO_DRY_RUN",
    "GET_SYMBOL_RULES_DRY_RUN",
    "GET_RATE_LIMITS_DRY_RUN",
    "GET_TIME_SYNC_DRY_RUN",
)

PROHIBITED_METHODS = (
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "TRANSFER_FUNDS",
    "WITHDRAW",
    "MODIFY_LEVERAGE",
    "REAL_RECONCILIATION_UNLOCK",
)

REQUIRED_PERMISSIONS = (
    "READ_ONLY_TESTNET",
    "MARKET_DATA_READ",
    "ACCOUNT_INFO_READ",
)


def create_design() -> DiscoveryDesign:
    return DiscoveryDesign(
        discovery_id=f"DSC_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        exchange_name="BINANCE_PLACEHOLDER",
        environment="TESTNET_PLACEHOLDER",
        endpoint_class="READ_ONLY_CANDIDATE",
        allowed_methods=ALLOWED_METHODS,
        prohibited_methods=PROHIBITED_METHODS,
        required_permissions=REQUIRED_PERMISSIONS,
        expected_response_schema={
            "account_metadata": {"type": "object", "fields": ["account_type", "permissions", "balances_placeholder"]},
            "exchange_info": {"type": "array", "items": {"symbol": "string", "status": "string"}},
            "rate_limits": {"type": "array", "items": {"rate_limit_type": "string", "interval": "string"}},
        },
        timeout_policy="PLACEHOLDER_30S",
        retry_policy="PLACEHOLDER_MAX_3_EXPONENTIAL_BACKOFF",
        audit_log_requirement="ALL_REQUESTS_LOGGED_REDACTED",
        final_decision="READ_ONLY_TESTNET_DISCOVERY_DESIGN_READY",
    )


def write_design(design: DiscoveryDesign, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(design.to_dict(), indent=2), encoding="utf-8")


def render_report(design: DiscoveryDesign) -> str:
    lines = ["# Read-Only Testnet Discovery Design", "",
        f"**discovery_id={design.discovery_id}**",
        f"**exchange={design.exchange_name}**",
        f"**environment={design.environment}**",
        f"**endpoint_class={design.endpoint_class}**",
        f"**final_decision={design.final_decision}**",
        "**REAL_NETWORK_NOT_ALLOWED**",
        "**TESTNET_SUBMIT_NOT_ALLOWED**", "",
        "## Allowed Methods", ""]
    for m in design.allowed_methods:
        lines.append(f"- {m}")
    lines.extend(["", "## Prohibited Methods", ""])
    for m in design.prohibited_methods:
        lines.append(f"- {m}")
    lines.extend(["", "## Required Permissions", ""])
    for p in design.required_permissions:
        lines.append(f"- {p}")
    lines.extend(["", "## Conclusion", "",
        "READ_ONLY_TESTNET_DISCOVERY_DESIGN_READY",
        "REAL_NETWORK_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
