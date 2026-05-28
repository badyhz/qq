"""T16001 — Frozen Approval Validator.

Pure deterministic. No I/O. No network.
Validates generated form templates and optionally completed forms.
No actual approval granted. No actual action performed.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

ALLOWED_DECISIONS: tuple[str, ...] = (
    "KEEP_FROZEN",
    "APPROVE_PREPARE_ARCHIVE_AFTER_BACKUP",
    "APPROVE_PREPARE_DELETE_AFTER_BACKUP",
    "APPROVE_PREPARE_OFFLINE_REWRITE",
    "REQUEST_MORE_REVIEW",
    "REJECT",
)

FORBIDDEN_DECISIONS: tuple[str, ...] = (
    "DELETE_NOW",
    "MOVE_NOW",
    "COPY_NOW",
    "ARCHIVE_NOW",
    "EXECUTE_NOW",
    "IMPORT_NOW",
    "ACTIVATE_LIVE",
    "ACTIVATE_TESTNET",
    "ENABLE_RUNTIME",
    "ENABLE_PLANNER",
)


@dataclass(frozen=True)
class ValidationCheck:
    """Single validation check result."""
    check_name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ValidationReport:
    """Full validation report."""
    checks: list[ValidationCheck]
    all_passed: bool
    release_hold: str
    total_checks: int
    passed_checks: int
    failed_checks: int

    def to_dict(self) -> dict:
        return {
            "checks": [c.to_dict() for c in self.checks],
            "all_passed": self.all_passed,
            "release_hold": self.release_hold,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
        }


def _check_required_fields(form: dict) -> ValidationCheck:
    required = [
        "form_id", "path", "form_type", "reviewer_name", "reviewer_role",
        "review_date", "candidate_action", "required_evidence_ids",
        "required_evidence_paths", "original_sha256", "original_size_bytes",
        "proposed_backup_path", "proposed_archive_path", "rollback_plan_id",
        "human_decision_placeholder", "decision_reason_placeholder",
        "approval_conditions", "rejection_conditions",
        "mandatory_confirmations", "forbidden_confirmations",
        "signature_placeholder", "release_hold", "advisory_only",
        "human_review_required",
    ]
    missing = [f for f in required if f not in form]
    return ValidationCheck(
        check_name=f"required_fields_{form.get('form_id', 'unknown')}",
        passed=(len(missing) == 0),
        detail=f"missing={missing}" if missing else "all fields present",
    )


def _check_decision_is_placeholder(form: dict) -> ValidationCheck:
    placeholder = form.get("human_decision_placeholder", "")
    is_placeholder = placeholder in ("PENDING_HUMAN_DECISION",)
    return ValidationCheck(
        check_name=f"decision_placeholder_{form.get('form_id', 'unknown')}",
        passed=is_placeholder,
        detail=f"human_decision_placeholder={placeholder!r}",
    )


def _check_release_hold(form: dict, expected: str) -> ValidationCheck:
    rh = form.get("release_hold", "")
    return ValidationCheck(
        check_name=f"release_hold_{form.get('form_id', 'unknown')}",
        passed=(rh == expected),
        detail=f"release_hold={rh!r}",
    )


def _check_advisory_only(form: dict) -> ValidationCheck:
    val = form.get("advisory_only", False)
    return ValidationCheck(
        check_name=f"advisory_only_{form.get('form_id', 'unknown')}",
        passed=(val is True),
        detail=f"advisory_only={val}",
    )


def _check_no_immediate_action(form: dict) -> ValidationCheck:
    decision = form.get("human_decision_placeholder", "")
    forbidden_in_decision = [fd for fd in FORBIDDEN_DECISIONS if fd in decision]
    return ValidationCheck(
        check_name=f"no_immediate_action_{form.get('form_id', 'unknown')}",
        passed=(len(forbidden_in_decision) == 0),
        detail=f"forbidden_in_decision={forbidden_in_decision}" if forbidden_in_decision else "no immediate action",
    )


def _check_forbidden_confirmations_listed(form: dict) -> ValidationCheck:
    forbidden = form.get("forbidden_confirmations", [])
    mandatory = form.get("mandatory_confirmations", [])
    leaked = [fc for fc in forbidden if fc in mandatory]
    return ValidationCheck(
        check_name=f"forbidden_confirmations_{form.get('form_id', 'unknown')}",
        passed=(len(leaked) == 0),
        detail=f"leaked_to_mandatory={leaked}" if leaked else "forbidden only in forbidden list",
    )


def validate_template(form: dict, release_hold: str) -> list[ValidationCheck]:
    """Validate a single generated form template."""
    return [
        _check_required_fields(form),
        _check_decision_is_placeholder(form),
        _check_release_hold(form, release_hold),
        _check_advisory_only(form),
        _check_no_immediate_action(form),
        _check_forbidden_confirmations_listed(form),
    ]


def _check_completed_reviewer(form: dict) -> ValidationCheck:
    reviewer = form.get("reviewer_name", "")
    is_placeholder = reviewer in ("PENDING_HUMAN_REVIEWER", "")
    # If form has a real decision, reviewer must be filled in
    decision = form.get("human_decision_placeholder", form.get("human_decision", ""))
    has_real_decision = decision not in ("PENDING_HUMAN_DECISION", "")
    needs_reviewer = has_real_decision and is_placeholder
    return ValidationCheck(
        check_name=f"completed_reviewer_{form.get('form_id', 'unknown')}",
        passed=not needs_reviewer,
        detail=f"reviewer={reviewer!r}, decision={decision!r}",
    )


def _check_completed_decision_valid(form: dict) -> ValidationCheck:
    decision = form.get("human_decision_placeholder", form.get("human_decision", ""))
    if decision in ("PENDING_HUMAN_DECISION", ""):
        return ValidationCheck(
            check_name=f"completed_decision_{form.get('form_id', 'unknown')}",
            passed=True,
            detail="still placeholder, no validation needed",
        )
    if decision in FORBIDDEN_DECISIONS:
        return ValidationCheck(
            check_name=f"completed_decision_{form.get('form_id', 'unknown')}",
            passed=False,
            detail=f"forbidden decision={decision!r}",
        )
    if decision not in ALLOWED_DECISIONS:
        return ValidationCheck(
            check_name=f"completed_decision_{form.get('form_id', 'unknown')}",
            passed=False,
            detail=f"unknown decision={decision!r}",
        )
    return ValidationCheck(
        check_name=f"completed_decision_{form.get('form_id', 'unknown')}",
        passed=True,
        detail=f"allowed decision={decision!r}",
    )


def _check_completed_no_immediate_override(form: dict) -> ValidationCheck:
    """Completed form cannot override release_hold."""
    rh = form.get("release_hold", "")
    return ValidationCheck(
        check_name=f"completed_release_hold_{form.get('form_id', 'unknown')}",
        passed=(rh == RELEASE_HOLD_REQUIRED),
        detail=f"release_hold={rh!r}",
    )


def validate_completed_form(form: dict, release_hold: str) -> list[ValidationCheck]:
    """Validate a completed form (if human has filled in decision)."""
    checks = validate_template(form, release_hold)
    checks.append(_check_completed_reviewer(form))
    checks.append(_check_completed_decision_valid(form))
    checks.append(_check_completed_no_immediate_override(form))
    return checks


def validate_forms(
    forms: list[dict],
    release_hold: str = RELEASE_HOLD_REQUIRED,
    completed: bool = False,
) -> ValidationReport:
    """Validate all forms."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    all_checks: list[ValidationCheck] = []
    for form in forms:
        if completed:
            all_checks.extend(validate_completed_form(form, release_hold))
        else:
            all_checks.extend(validate_template(form, release_hold))

    all_passed = all(c.passed for c in all_checks)
    return ValidationReport(
        checks=all_checks,
        all_passed=all_passed,
        release_hold=release_hold,
        total_checks=len(all_checks),
        passed_checks=sum(1 for c in all_checks if c.passed),
        failed_checks=sum(1 for c in all_checks if not c.passed),
    )


def render_validation_markdown(report: ValidationReport) -> str:
    lines = [
        "# Frozen Approval Validation Report",
        "",
        f"**Total checks:** {report.total_checks}",
        f"**Passed:** {report.passed_checks}",
        f"**Failed:** {report.failed_checks}",
        f"**All passed:** {report.all_passed}",
        f"**release_hold:** {report.release_hold}",
        "",
        "## Checks",
        "",
    ]

    for check in report.checks:
        status = "PASS" if check.passed else "FAIL"
        lines.append(f"- **{check.check_name}:** {status} - {check.detail}")

    lines.append("")
    return "\n".join(lines)


def load_forms(path: pathlib.Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("items", [])


def write_json(report: ValidationReport, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def write_manifest(report: ValidationReport, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "total_checks": report.total_checks,
        "passed_checks": report.passed_checks,
        "failed_checks": report.failed_checks,
        "all_passed": report.all_passed,
        "release_hold": report.release_hold,
        "validation_hash": hashlib.sha256(
            json.dumps(report.to_dict(), sort_keys=True, indent=2).encode()
        ).hexdigest(),
    }
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(report: ValidationReport, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_validation_markdown(report), encoding="utf-8")
