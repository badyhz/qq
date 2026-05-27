from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyAdapterInput:
    adapter_id: str
    run_id: str
    mode: str
    requested_view: str
    symbols: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyAdapterOutput:
    ok: bool
    view_name: str
    sanitized_payload: Dict[str, Any]
    failure_codes: List[str]
    notes: List[str] = field(default_factory=list)


_VALID_MODES = {"dry-run", "live", "shadow", "paper"}
_VALID_VIEWS = {"summary", "positions", "orders", "risk"}


def build_readonly_adapter_input_sample(kind: str) -> RuntimeGovernanceReadOnlyAdapterInput:
    """Build sample input by kind. Raises ValueError for unknown kind."""
    if kind == "valid_summary":
        return RuntimeGovernanceReadOnlyAdapterInput(
            adapter_id="adapter-001",
            run_id="run-abc",
            mode="dry-run",
            requested_view="summary",
            symbols=["BTCUSDT", "ETHUSDT"],
        )
    elif kind == "missing_adapter":
        return RuntimeGovernanceReadOnlyAdapterInput(
            adapter_id="",
            run_id="run-abc",
            mode="dry-run",
            requested_view="summary",
            symbols=["BTCUSDT"],
        )
    elif kind == "invalid_mode":
        return RuntimeGovernanceReadOnlyAdapterInput(
            adapter_id="adapter-001",
            run_id="run-abc",
            mode="forbidden-mode",
            requested_view="summary",
            symbols=["BTCUSDT"],
        )
    elif kind == "empty_symbols":
        return RuntimeGovernanceReadOnlyAdapterInput(
            adapter_id="adapter-001",
            run_id="run-abc",
            mode="dry-run",
            requested_view="summary",
            symbols=[],
        )
    else:
        raise ValueError(f"Unknown sample kind: {kind}")


def validate_readonly_adapter_input(inp: RuntimeGovernanceReadOnlyAdapterInput) -> bool:
    """Validate input. Pure."""
    if not inp.adapter_id:
        return False
    if not inp.run_id:
        return False
    if inp.mode not in _VALID_MODES:
        return False
    if inp.requested_view not in _VALID_VIEWS:
        return False
    if not inp.symbols:
        return False
    return True


def readonly_adapter_input_to_dict(inp: RuntimeGovernanceReadOnlyAdapterInput) -> Dict[str, Any]:
    """Serialize."""
    return {
        "adapter_id": inp.adapter_id,
        "run_id": inp.run_id,
        "mode": inp.mode,
        "requested_view": inp.requested_view,
        "symbols": list(inp.symbols),
        "metadata": dict(inp.metadata),
    }


def readonly_adapter_output_to_dict(out: RuntimeGovernanceReadOnlyAdapterOutput) -> Dict[str, Any]:
    """Serialize."""
    return {
        "ok": out.ok,
        "view_name": out.view_name,
        "sanitized_payload": dict(out.sanitized_payload),
        "failure_codes": list(out.failure_codes),
        "notes": list(out.notes),
    }
