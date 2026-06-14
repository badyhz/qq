"""Read-only adapter contract."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class AdapterMethod:
    method_id: str
    name: str
    http_method: str
    endpoint_template: str
    required_params: tuple[str, ...]
    response_schema: str
    read_only: bool
    def to_dict(self) -> dict:
        return {
            "method_id": self.method_id, "name": self.name,
            "http_method": self.http_method, "endpoint_template": self.endpoint_template,
            "required_params": list(self.required_params),
            "response_schema": self.response_schema, "read_only": self.read_only,
        }


@dataclass(frozen=True)
class ReadonlyAdapterContract:
    contract_id: str
    created_at: str
    exchange: str
    environment: str
    methods: tuple[AdapterMethod, ...]
    def to_dict(self) -> dict:
        return {"contract_id": self.contract_id, "created_at": self.created_at,
                "exchange": self.exchange, "environment": self.environment,
                "methods": [m.to_dict() for m in self.methods]}


METHODS = (
    AdapterMethod("MTH_001", "build_discovery_request_dry_run", "N/A", "N/A", (), "DiscoveryRequestEnvelope", True),
    AdapterMethod("MTH_002", "validate_readonly_permission_dry_run", "N/A", "N/A", ("permission_scope",), "PermissionValidationResult", True),
    AdapterMethod("MTH_003", "render_exchange_info_request_dry_run", "GET", "/api/v3/exchangeInfo", (), "ExchangeInfoResponse", True),
    AdapterMethod("MTH_004", "render_symbol_rules_request_dry_run", "GET", "/api/v3/exchangeInfo?symbol={symbol}", ("symbol",), "SymbolRulesResponse", True),
    AdapterMethod("MTH_005", "render_rate_limit_request_dry_run", "GET", "/api/v3/exchangeInfo", (), "RateLimitResponse", True),
    AdapterMethod("MTH_006", "render_time_sync_request_dry_run", "GET", "/api/v3/time", (), "TimeSyncResponse", True),
    AdapterMethod("MTH_007", "render_discovery_audit_record_dry_run", "N/A", "N/A", (), "AuditRecord", True),
)


def create_contract() -> ReadonlyAdapterContract:
    return ReadonlyAdapterContract(
        contract_id=f"ADC_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        exchange="BINANCE_PLACEHOLDER",
        environment="TESTNET_PLACEHOLDER",
        methods=METHODS,
    )


def validate_contract(contract: ReadonlyAdapterContract) -> list[dict]:
    errors = []
    forbidden = ("submit_order", "cancel_order", "place_order", "market_order", "limit_order", "real_reconcile", "unlock_submit")
    for m in contract.methods:
        for f in forbidden:
            if f in m.name.lower():
                errors.append(f"Forbidden method: {m.name}")
        if not m.read_only:
            errors.append(f"Method not read-only: {m.name}")
    return [{"valid": len(errors) == 0, "errors": errors}]


def write_contract(contract: ReadonlyAdapterContract, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(contract.to_dict(), indent=2), encoding="utf-8")


def render_report(contract: ReadonlyAdapterContract) -> str:
    lines = ["# Read-Only Adapter Contract", "",
        f"**contract_id={contract.contract_id}**",
        f"**exchange={contract.exchange}**",
        f"**environment={contract.environment}**",
        f"**methods={len(contract.methods)}**",
        "**REAL_ADAPTER_IMPLEMENTATION_NOT_ALLOWED**", "",
        "## Methods", "",
        "| ID | Name | HTTP | Endpoint | Read-Only |",
        "|----|------|------|----------|-----------|"]
    for m in contract.methods:
        lines.append(f"| {m.method_id} | {m.name} | {m.http_method} | {m.endpoint_template} | {m.read_only} |")
    lines.extend(["", "## Conclusion", "",
        "READ_ONLY_ADAPTER_CONTRACT_READY",
        "REAL_ADAPTER_IMPLEMENTATION_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
