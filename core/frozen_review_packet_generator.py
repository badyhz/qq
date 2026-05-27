"""T1445 - Frozen review packet generator.

Pure functions. No I/O. No network. No random. No timestamps. No env reads.
"""
from __future__ import annotations

from core.frozen_file_review_packet import FrozenFileReviewPacket, build_review_packet
from core.frozen_review_check import FrozenReviewCheck, build_review_check

# Standard checks for all risk classes
_BASE_CHECKS: tuple[tuple[str, str, str, str], ...] = (
    ("RC-001", "No live imports", "IMPORT_BOUNDARY", "Verify file does not import live/submit/exchange modules"),
    ("RC-002", "No network calls", "NETWORK_FREE", "Verify file makes no network or socket calls"),
    ("RC-003", "No hardcoded credentials", "CREDENTIAL_FREE", "Verify file contains no secrets or API keys"),
    ("RC-004", "No side effects", "SIDE_EFFECT_FREE", "Verify file has no filesystem writes or process spawns"),
)

# Additional checks for HIGH-risk files
_HIGH_EXTRA_CHECKS: tuple[tuple[str, str, str, str], ...] = (
    ("RC-005", "Dry-run only", "DRY_RUN_ONLY", "Verify file only operates in dry-run mode"),
    ("RC-006", "Human approved", "HUMAN_APPROVED", "Verify file has explicit human approval on record"),
)

# Evidence requirements by risk class
_HIGH_EVIDENCE: tuple[str, ...] = (
    "static_analysis_report",
    "import_boundary_audit",
    "human_approval_record",
    "dry_run_test_output",
    "side_effect_scan_report",
)

_MEDIUM_EVIDENCE: tuple[str, ...] = (
    "static_analysis_report",
    "import_boundary_audit",
)


def generate_review_packet(file_path: str, risk_class: str) -> FrozenFileReviewPacket:
    """Generate a deterministic review packet for a frozen file.

    HIGH-risk files get 6 checks and 5 evidence requirements.
    MEDIUM-risk files get 4 checks and 2 evidence requirements.

    Pure function. No I/O.
    """
    is_high = risk_class == "HIGH"

    checks_spec = _BASE_CHECKS + (_HIGH_EXTRA_CHECKS if is_high else ())
    checks = tuple(
        build_review_check(
            check_id=cid,
            check_name=name,
            check_type=ctype,
            description=desc,
        )
        for cid, name, ctype, desc in checks_spec
    )

    evidence = _HIGH_EVIDENCE if is_high else _MEDIUM_EVIDENCE
    category = "script" if file_path.startswith("scripts/") else "core"

    return build_review_packet(
        packet_id=f"PKT-{file_path.replace('/', '-')}",
        file_path=file_path,
        risk_class=risk_class,
        file_category=category,
        review_checks=checks,
        evidence_requirements=evidence,
    )
