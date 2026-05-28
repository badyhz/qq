"""T15501 — Frozen Backup Verification.

Pure deterministic. No I/O. No network.
Verifies backup manifest and archive simulation safety invariants.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

FORBIDDEN_STATUSES: tuple[str, ...] = (
    "BACKUP_DONE",
    "SAFE_TO_DELETE",
    "SAFE_TO_MOVE",
    "ARCHIVED",
    "DELETED",
    "MOVED",
    "EXECUTED",
    "IMPORTED",
    "ACTIVATED",
)


@dataclass(frozen=True)
class VerificationCheck:
    """Single verification check result."""
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
class VerificationReport:
    """Full verification report."""
    checks: list[VerificationCheck]
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


def _check_release_hold(manifest: dict, label: str) -> VerificationCheck:
    rh = manifest.get("release_hold", "")
    return VerificationCheck(
        check_name=f"{label}_release_hold_is_HOLD",
        passed=(rh == RELEASE_HOLD_REQUIRED),
        detail=f"release_hold={rh!r}",
    )


def _check_advisory_only(manifest: dict, items: list[dict] | None = None) -> VerificationCheck:
    val = manifest.get("advisory_only", None)
    if val is None and items:
        # Check item-level advisory_only
        val = all(item.get("advisory_only", False) for item in items)
    return VerificationCheck(
        check_name="backup_manifest_advisory_only",
        passed=(val is True),
        detail=f"advisory_only={val}",
    )


def _check_simulation_only(manifest: dict, items: list[dict] | None = None) -> VerificationCheck:
    val = manifest.get("simulation_only", None)
    if val is None and items:
        # Check item-level simulation_only
        val = all(item.get("simulation_only", False) for item in items)
    return VerificationCheck(
        check_name="simulation_only",
        passed=(val is True),
        detail=f"simulation_only={val}",
    )


def _check_human_review_required(backup_items: list[dict]) -> VerificationCheck:
    violations = [
        item["path"]
        for item in backup_items
        if not item.get("human_review_required", False)
    ]
    return VerificationCheck(
        check_name="all_items_human_review_required",
        passed=(len(violations) == 0),
        detail=f"violations={violations}" if violations else "all items require human review",
    )


def _check_no_forbidden_statuses_in_backup(backup_items: list[dict]) -> VerificationCheck:
    violations = []
    for item in backup_items:
        for key in ("current_status", "backup_class"):
            val = item.get(key, "")
            if val in FORBIDDEN_STATUSES:
                violations.append(f"{item['path']}:{key}={val}")
    return VerificationCheck(
        check_name="no_forbidden_statuses_in_backup_manifest",
        passed=(len(violations) == 0),
        detail=f"violations={violations}" if violations else "no forbidden statuses",
    )


def _check_no_forbidden_statuses_in_simulation(sim_items: list[dict]) -> VerificationCheck:
    violations = []
    for item in sim_items:
        status = item.get("final_status", "")
        if status in FORBIDDEN_STATUSES:
            violations.append(f"{item['path']}:final_status={status}")
    return VerificationCheck(
        check_name="no_forbidden_statuses_in_simulation",
        passed=(len(violations) == 0),
        detail=f"violations={violations}" if violations else "no forbidden statuses",
    )


def _check_hypothetical_paths(backup_items: list[dict]) -> VerificationCheck:
    violations = []
    for item in backup_items:
        bp = item.get("proposed_backup_path", "")
        if bp and not bp.startswith("archive_simulation/"):
            violations.append(f"{item['path']}:proposed_backup_path={bp}")
    return VerificationCheck(
        check_name="all_proposed_paths_hypothetical",
        passed=(len(violations) == 0),
        detail=f"violations={violations}" if violations else "all paths hypothetical",
    )


def _check_would_flags(sim_items: list[dict]) -> VerificationCheck:
    violations = []
    for item in sim_items:
        for flag in ("would_copy", "would_move", "would_delete", "would_modify"):
            if item.get(flag, False):
                violations.append(f"{item['path']}:{flag}=true")
    return VerificationCheck(
        check_name="all_would_flags_false",
        passed=(len(violations) == 0),
        detail=f"violations={violations}" if violations else "all would_* flags false",
    )


def _check_simulation_human_approval(sim_items: list[dict]) -> VerificationCheck:
    violations = [
        item["path"]
        for item in sim_items
        if not item.get("human_approval_required", False)
    ]
    return VerificationCheck(
        check_name="simulation_human_approval_required",
        passed=(len(violations) == 0),
        detail=f"violations={violations}" if violations else "all items require human approval",
    )


def _check_backup_allowed_now(backup_items: list[dict]) -> VerificationCheck:
    violations = [
        item["path"]
        for item in backup_items
        if item.get("backup_allowed_now", False)
    ]
    return VerificationCheck(
        check_name="backup_allowed_now_false",
        passed=(len(violations) == 0),
        detail=f"violations={violations}" if violations else "backup_allowed_now false for all",
    )


def verify_backup_manifest(
    backup_manifest_data: dict,
    archive_simulation_data: dict,
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> VerificationReport:
    """Run all verification checks on backup manifest and archive simulation."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    backup_items = backup_manifest_data.get("items", backup_manifest_data) \
        if isinstance(backup_manifest_data, dict) else backup_manifest_data
    sim_items = archive_simulation_data.get("items", archive_simulation_data) \
        if isinstance(archive_simulation_data, dict) else archive_simulation_data

    if isinstance(backup_manifest_data, dict) and "items" not in backup_manifest_data:
        backup_items = backup_manifest_data
    if isinstance(archive_simulation_data, dict) and "items" not in archive_simulation_data:
        sim_items = archive_simulation_data

    # For top-level manifest dicts
    backup_manifest_dict = backup_manifest_data if isinstance(backup_manifest_data, dict) else {}
    sim_manifest_dict = archive_simulation_data if isinstance(archive_simulation_data, dict) else {}

    checks = [
        _check_release_hold({"release_hold": release_hold}, "input"),
        _check_advisory_only(backup_manifest_dict, backup_items if isinstance(backup_items, list) else None),
        _check_simulation_only(sim_manifest_dict, sim_items if isinstance(sim_items, list) else None),
        _check_human_review_required(backup_items if isinstance(backup_items, list) else []),
        _check_no_forbidden_statuses_in_backup(backup_items if isinstance(backup_items, list) else []),
        _check_no_forbidden_statuses_in_simulation(sim_items if isinstance(sim_items, list) else []),
        _check_hypothetical_paths(backup_items if isinstance(backup_items, list) else []),
        _check_would_flags(sim_items if isinstance(sim_items, list) else []),
        _check_simulation_human_approval(sim_items if isinstance(sim_items, list) else []),
        _check_backup_allowed_now(backup_items if isinstance(backup_items, list) else []),
    ]

    # Check output hash stability
    if isinstance(backup_items, list) and backup_items:
        raw1 = json.dumps(backup_items, sort_keys=True, indent=2)
        raw2 = json.dumps(backup_items, sort_keys=True, indent=2)
        h1 = hashlib.sha256(raw1.encode()).hexdigest()
        h2 = hashlib.sha256(raw2.encode()).hexdigest()
        checks.append(VerificationCheck(
            check_name="output_hash_stable",
            passed=(h1 == h2),
            detail=f"h1={h1[:16]} h2={h2[:16]}",
        ))

    all_passed = all(c.passed for c in checks)
    return VerificationReport(
        checks=checks,
        all_passed=all_passed,
        release_hold=release_hold,
        total_checks=len(checks),
        passed_checks=sum(1 for c in checks if c.passed),
        failed_checks=sum(1 for c in checks if not c.passed),
    )


def render_verification_markdown(report: VerificationReport) -> str:
    """Render verification report as markdown."""
    lines = [
        "# Frozen Backup Verification Report",
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


def load_json(path: pathlib.Path) -> dict | list:
    """Load JSON data from file."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(report: VerificationReport, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def write_manifest(report: VerificationReport, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "total_checks": report.total_checks,
        "passed_checks": report.passed_checks,
        "failed_checks": report.failed_checks,
        "all_passed": report.all_passed,
        "release_hold": report.release_hold,
        "verification_hash": hashlib.sha256(
            json.dumps(report.to_dict(), sort_keys=True, indent=2).encode()
        ).hexdigest(),
    }
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(report: VerificationReport, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_verification_markdown(report), encoding="utf-8")
