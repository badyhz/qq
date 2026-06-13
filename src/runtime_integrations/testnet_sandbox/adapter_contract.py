"""Adapter contract interface for testnet sandbox."""
from __future__ import annotations
import json, pathlib
from abc import ABC, abstractmethod
from .sandbox_types import OrderIntent, SimulatedSubmitResult, SimulatedBalance, SimulatedPosition, ConnectionConfig, ValidationResult

class SandboxAdapterContract(ABC):
    @abstractmethod
    def validate_connection_config(self, config: ConnectionConfig) -> ValidationResult:
        ...

    @abstractmethod
    def build_order_intent(self, symbol: str, side: str, order_type: str, quantity: float, price: float | None, source_signal_id: str) -> OrderIntent:
        ...

    @abstractmethod
    def validate_order_intent(self, intent: OrderIntent) -> ValidationResult:
        ...

    @abstractmethod
    def simulate_submit(self, intent: OrderIntent) -> SimulatedSubmitResult:
        ...

    @abstractmethod
    def simulate_cancel(self, order_id: str, symbol: str) -> SimulatedSubmitResult:
        ...

    @abstractmethod
    def get_simulated_balance(self, asset: str) -> SimulatedBalance:
        ...

    @abstractmethod
    def get_simulated_positions(self) -> tuple[SimulatedPosition, ...]:
        ...

def validate_contract_implementation(cls: type) -> tuple[bool, tuple[str, ...]]:
    required = ("validate_connection_config", "build_order_intent", "validate_order_intent", "simulate_submit", "simulate_cancel", "get_simulated_balance", "get_simulated_positions")
    missing = []
    for m in required:
        if not hasattr(cls, m) or not callable(getattr(cls, m, None)):
            missing.append(m)
    return (len(missing) == 0, tuple(missing))

def write_contract_validation(result: tuple[bool, tuple[str, ...]], cls_name: str, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {"class": cls_name, "valid": result[0], "missing_methods": list(result[1])}
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
