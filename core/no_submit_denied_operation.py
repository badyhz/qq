from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoSubmitDeniedOperation:
    operation: str
    category: str
    severity: str
    description: str


DENIED_OPERATIONS: tuple[NoSubmitDeniedOperation, ...] = (
    NoSubmitDeniedOperation(
        operation="place_order",
        category="execution",
        severity="critical",
        description="Submit a new order to the exchange",
    ),
    NoSubmitDeniedOperation(
        operation="cancel_order",
        category="execution",
        severity="critical",
        description="Cancel an existing order on the exchange",
    ),
    NoSubmitDeniedOperation(
        operation="modify_order",
        category="execution",
        severity="critical",
        description="Modify an existing order on the exchange",
    ),
    NoSubmitDeniedOperation(
        operation="close_position",
        category="position",
        severity="critical",
        description="Close an open position on the exchange",
    ),
    NoSubmitDeniedOperation(
        operation="open_position",
        category="position",
        severity="critical",
        description="Open a new position on the exchange",
    ),
    NoSubmitDeniedOperation(
        operation="transfer_funds",
        category="account",
        severity="critical",
        description="Transfer funds between accounts",
    ),
)
