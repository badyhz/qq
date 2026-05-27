"""T1601 - Frozen Backlog Report Validator.

Validates frozen backlog report dicts/files against expected structure.
Pure functions. Only validate_report_file has file I/O (reading).
No network. No live. No submit.
"""
from __future__ import annotations

import json

from core.frozen_backlog_validation_result import (
    FrozenBacklogValidationResult,
    build_validation_result,
)

# --- Expected constants ---

_EXPECTED_RELEASE_HOLD = "HOLD"
_EXPECTED_TOTAL_FILES = 22
_EXPECTED_HIGH_RISK_COUNT = 9
_EXPECTED_MEDIUM_RISK_COUNT = 13

_EXPECTED_SUMMARY_FIELDS = frozenset({
    "summary_id",
    "total_files",
    "high_risk_count",
    "medium_risk_count",
    "release_hold",
    "no_live",
    "no_submit",
    "no_exchange",
    "no_runtime_integration",
    "no_planner_integration",
})

_EXPECTED_RECORD_FIELDS = frozenset({
    "record_id",
    "file_path",
    "risk_class",
    "category",
    "allowed_actions",
    "forbidden_actions",
    "required_evidence",
    "readiness_score",
    "unlock_recommendation",
    "release_hold",
})

_EXPECTED_SAFETY_FLAGS = ("no_live", "no_submit", "no_exchange",
                           "no_runtime_integration", "no_planner_integration")


def validate_report_data(data: dict) -> FrozenBacklogValidationResult:
    """Validate a report dict (as loaded from JSON).

    Pure function. No I/O. No network.

    Checks:
    1. Top-level 'summary' and 'records' keys exist
    2. Summary has all required fields
    3. total_files == 22
    4. high_risk_count == 9
    5. medium_risk_count == 13
    6. release_hold == "HOLD"
    7. All safety flags (no_live etc.) are True
    8. Each record has all required fields
    9. Each record's release_hold == "HOLD"
    10. records count == total_files
    """
    passed: list[str] = []
    failed: list[str] = []

    # --- Check top-level keys ---
    if "summary" not in data:
        return build_validation_result(
            is_valid=False,
            checks_passed=tuple(passed),
            checks_failed=("missing_summary_key",),
            error_message="Missing 'summary' key in report data.",
        )
    if "records" not in data:
        return build_validation_result(
            is_valid=False,
            checks_passed=tuple(passed),
            checks_failed=("missing_records_key",),
            error_message="Missing 'records' key in report data.",
        )

    summary = data["summary"]
    records = data["records"]

    # --- Summary field presence ---
    actual_summary_fields = frozenset(summary.keys())
    if actual_summary_fields == _EXPECTED_SUMMARY_FIELDS:
        passed.append("summary_fields_present")
    else:
        failed.append("summary_fields_present")

    # --- total_files ---
    if summary.get("total_files") == _EXPECTED_TOTAL_FILES:
        passed.append("total_files_count")
    else:
        failed.append("total_files_count")

    # --- high_risk_count ---
    if summary.get("high_risk_count") == _EXPECTED_HIGH_RISK_COUNT:
        passed.append("high_risk_count")
    else:
        failed.append("high_risk_count")

    # --- medium_risk_count ---
    if summary.get("medium_risk_count") == _EXPECTED_MEDIUM_RISK_COUNT:
        passed.append("medium_risk_count")
    else:
        failed.append("medium_risk_count")

    # --- release_hold ---
    if summary.get("release_hold") == _EXPECTED_RELEASE_HOLD:
        passed.append("summary_release_hold")
    else:
        failed.append("summary_release_hold")

    # --- Safety flags ---
    for flag in _EXPECTED_SAFETY_FLAGS:
        check_id = f"safety_{flag}"
        if summary.get(flag) is True:
            passed.append(check_id)
        else:
            failed.append(check_id)

    # --- Records count matches total_files ---
    if len(records) == _EXPECTED_TOTAL_FILES:
        passed.append("records_count_match")
    else:
        failed.append("records_count_match")

    # --- Per-record validation ---
    for idx, record in enumerate(records):
        prefix = f"record_{idx}"

        # All required fields present
        actual_rec_fields = frozenset(record.keys())
        if actual_rec_fields == _EXPECTED_RECORD_FIELDS:
            passed.append(f"{prefix}_fields")
        else:
            failed.append(f"{prefix}_fields")

        # Record release_hold
        if record.get("release_hold") == _EXPECTED_RELEASE_HOLD:
            passed.append(f"{prefix}_release_hold")
        else:
            failed.append(f"{prefix}_release_hold")

    is_valid = len(failed) == 0
    error_msg = "" if is_valid else f"Failed checks: {', '.join(failed)}"

    return build_validation_result(
        is_valid=is_valid,
        checks_passed=tuple(passed),
        checks_failed=tuple(failed),
        error_message=error_msg,
    )


def validate_report_file(json_path: str) -> FrozenBacklogValidationResult:
    """Read a JSON report file and validate it.

    This is the only function with file I/O (reading).
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return build_validation_result(
            is_valid=False,
            checks_passed=(),
            checks_failed=("file_read",),
            error_message=f"Failed to read/parse JSON: {exc}",
        )
    return validate_report_data(data)
