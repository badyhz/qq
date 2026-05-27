"""T1614 - Frozen Backlog Verdict Engine.

Pure functions for computing verdicts from diffs and validation results.
No I/O. No timestamps. No network.
"""
from __future__ import annotations

from core.frozen_backlog_diff import FrozenBacklogDiff
from core.frozen_backlog_validation_result import FrozenBacklogValidationResult
from core.frozen_backlog_verdict import FrozenBacklogVerdict, build_verdict


# Fields that cause FAIL (dangerous changes)
_DANGEROUS_FIELDS = frozenset({
    "risk_class",
    "release_hold",
    "total_files",
    "high_risk_count",
    "medium_risk_count",
})

# Fields that cause PARTIAL (non-dangerous metadata changes)
_NON_DANGEROUS_FIELDS = frozenset({
    "unlock_recommendation",
    "readiness_score",
    "category",
})


def _collect_changed_fields(diff: FrozenBacklogDiff) -> tuple[str, ...]:
    """Collect all changed field names from a diff. Pure function."""
    fields: list[str] = []
    if diff.added_files:
        fields.append("added_files")
    if diff.removed_files:
        fields.append("removed_files")
    for change in diff.risk_class_changes:
        fields.append(f"risk_class:{change.file_path}")
    for change in diff.category_changes:
        fields.append(f"category:{change.file_path}")
    for change in diff.recommendation_changes:
        fields.append(f"unlock_recommendation:{change.file_path}")
    for change in diff.safety_flag_changes:
        fields.append(f"safety_flag:{change.file_path}:{change.field_name}")
    for change in diff.hold_changes:
        fields.append(f"release_hold:{change.file_path}")
    return tuple(fields)


def _has_dangerous_changes(diff: FrozenBacklogDiff) -> bool:
    """Check if diff has dangerous field changes. Pure function."""
    if diff.added_files or diff.removed_files:
        return True
    for change in diff.risk_class_changes:
        if change.field_name in _DANGEROUS_FIELDS:
            return True
    for change in diff.hold_changes:
        return True
    for change in diff.safety_flag_changes:
        return True
    return False


def _has_non_dangerous_changes(diff: FrozenBacklogDiff) -> bool:
    """Check if diff has only non-dangerous metadata changes. Pure function."""
    for change in diff.recommendation_changes:
        return True
    for change in diff.category_changes:
        return True
    return False


def compute_verdict(
    diff: FrozenBacklogDiff,
    validation_result: FrozenBacklogValidationResult,
) -> FrozenBacklogVerdict:
    """Compute PASS / PARTIAL / FAIL verdict. Pure function.

    PASS: no changes and validation passed
    PARTIAL: non-dangerous metadata changed (recommendation, readiness)
    FAIL: counts, risk class, safety flags, hold, or frozen file inventory changed
    """
    from core.frozen_backlog_diff_engine import has_changes

    changed = _collect_changed_fields(diff)

    # FAIL if validation failed
    if not validation_result.is_valid:
        return build_verdict(
            verdict="FAIL",
            notes=f"Validation failed: {validation_result.error_message}",
            changed_fields=changed,
            risk_level="CRITICAL",
        )

    # No changes → PASS
    if not has_changes(diff):
        return build_verdict(
            verdict="PASS",
            notes="No changes detected. Validation passed.",
            changed_fields=(),
            risk_level="SAFE",
        )

    # Dangerous changes → FAIL
    if _has_dangerous_changes(diff):
        return build_verdict(
            verdict="FAIL",
            notes="Dangerous changes detected (risk class, hold, safety flags, or file inventory).",
            changed_fields=changed,
            risk_level="CRITICAL",
        )

    # Only non-dangerous → PARTIAL
    if _has_non_dangerous_changes(diff):
        return build_verdict(
            verdict="PARTIAL",
            notes="Non-dangerous metadata changes only (recommendation, category).",
            changed_fields=changed,
            risk_level="CAUTION",
        )

    # Fallback
    return build_verdict(
        verdict="FAIL",
        notes="Unhandled change type detected.",
        changed_fields=changed,
        risk_level="CRITICAL",
    )
