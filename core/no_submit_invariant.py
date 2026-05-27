from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoSubmitInvariant:
    invariant_id: str
    description: str
    check_function_name: str


INVARIANTS: tuple[NoSubmitInvariant, ...] = (
    NoSubmitInvariant(
        invariant_id="INV-001",
        description="No order placement",
        check_function_name="check_no_order_placement",
    ),
    NoSubmitInvariant(
        invariant_id="INV-002",
        description="No position modification",
        check_function_name="check_no_position_modification",
    ),
    NoSubmitInvariant(
        invariant_id="INV-003",
        description="No account mutation",
        check_function_name="check_no_account_mutation",
    ),
    NoSubmitInvariant(
        invariant_id="INV-004",
        description="No exchange API calls",
        check_function_name="check_no_exchange_api_calls",
    ),
)
