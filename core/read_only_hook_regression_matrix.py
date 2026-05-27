"""Read-only hook regression matrix — pure frozen dataclasses, no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class RegressionTestCase:
    test_id: str
    description: str
    expected_status: str
    category: str


def build_default_regression_matrix() -> List[RegressionTestCase]:
    return [
        RegressionTestCase("reg_01", "Valid query operation succeeds", "success", "contract"),
        RegressionTestCase("reg_02", "Denied permission returns denied status", "denied", "permission"),
        RegressionTestCase("reg_03", "Unknown permission returns denied status", "denied", "permission"),
        RegressionTestCase("reg_04", "Mutation operation kind rejected", "error", "invariant"),
        RegressionTestCase("reg_05", "Secret keys are redacted in output", "success", "sanitization"),
        RegressionTestCase("reg_06", "Non-secret keys pass through unchanged", "success", "sanitization"),
        RegressionTestCase("reg_07", "Network context keys trigger invariant failure", "error", "invariant"),
        RegressionTestCase("reg_08", "Empty side_effects_declared accepted", "success", "contract"),
        RegressionTestCase("reg_09", "Non-empty side_effects_declared raises error", "error", "contract"),
        RegressionTestCase("reg_10", "Invalid operation_kind raises ValueError", "error", "contract"),
        RegressionTestCase("reg_11", "Invalid result_status raises ValueError", "error", "contract"),
        RegressionTestCase("reg_12", "Frozen dataclass rejects attribute mutation", "error", "contract"),
        RegressionTestCase("reg_13", "Serializer returns plain dict copy", "success", "serializer"),
        RegressionTestCase("reg_14", "Invariant check covers all five IDs", "success", "invariant"),
        RegressionTestCase("reg_15", "Failure classifier maps known categories", "success", "failure"),
        RegressionTestCase("reg_16", "Unknown failure category maps to UNKNOWN", "success", "failure"),
        RegressionTestCase("reg_17", "Review checklist defaults to PENDING", "success", "review"),
        RegressionTestCase("reg_18", "Rollout hold defaults to active HOLD", "success", "rollout"),
        RegressionTestCase("reg_19", "Observability event validates observation point", "success", "observability"),
        RegressionTestCase("reg_20", "Invalid observation point raises ValueError", "error", "observability"),
    ]


def regression_test_case_to_dict(tc: RegressionTestCase) -> dict:
    return {
        "test_id": tc.test_id,
        "description": tc.description,
        "expected_status": tc.expected_status,
        "category": tc.category,
    }
