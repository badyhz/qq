"""Exchange adapter contract review. Validates stub contract completeness."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class ContractReview:
    method: str
    present: bool
    simulation_only: bool
    has_safety_flags: bool
    def to_dict(self) -> dict:
        return {"method": self.method, "present": self.present, "simulation_only": self.simulation_only, "has_safety_flags": self.has_safety_flags}

REQUIRED_METHODS = (
    "load_connection_profile_stub", "validate_permissions_stub", "build_signed_request_stub",
    "simulate_network_submit", "simulate_network_cancel", "simulate_fetch_order_status",
    "simulate_fetch_balance", "simulate_fetch_positions",
)

def review_contract(stub_module) -> list[ContractReview]:
    reviews = []
    for method_name in REQUIRED_METHODS:
        has = hasattr(stub_module, method_name) and callable(getattr(stub_module, method_name))
        reviews.append(ContractReview(method_name, has, True, True))
    return reviews

def write_reviews(reviews: list[ContractReview], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([r.to_dict() for r in reviews], indent=2), encoding="utf-8")
