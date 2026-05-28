"""Offline research governance — validate docs, experiments, and safety boundaries.

No network. No exchange. No runtime. No planner. Advisory only.
release_hold remains HOLD.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

REQUIRED_OPERATOR_MANUALS = [
    "operator_manuals/offline_research_stack_operator_manual.md",
    "operator_manuals/offline_research_stack_quickstart.md",
    "operator_manuals/offline_research_stack_command_reference.md",
    "operator_manuals/offline_research_stack_artifact_reference.md",
    "operator_manuals/offline_research_stack_safety_manual.md",
    "operator_manuals/offline_research_stack_troubleshooting.md",
    "operator_manuals/offline_research_stack_faq.md",
]

REQUIRED_RUNBOOKS = [
    "runbooks/run_full_offline_research_stack.md",
    "runbooks/run_quality_gate_only.md",
    "runbooks/run_artifact_browser_only.md",
    "runbooks/run_comparison_analytics_only.md",
    "runbooks/run_human_review_packet_only.md",
    "runbooks/rerun_reproducibility_check.md",
    "runbooks/validate_release_hold_boundary.md",
    "runbooks/recover_from_failed_artifact_browser.md",
    "runbooks/recover_from_failed_comparison.md",
    "runbooks/recover_from_failed_human_review.md",
    "runbooks/offline_stack_clean_tmp_outputs.md",
    "runbooks/offline_stack_preflight_check.md",
    "runbooks/offline_stack_postflight_check.md",
]

REQUIRED_CHECKLISTS = [
    "checklists/offline_research_preflight_checklist.md",
    "checklists/offline_research_postflight_checklist.md",
    "checklists/quality_gate_review_checklist.md",
    "checklists/artifact_browser_review_checklist.md",
    "checklists/comparison_analytics_review_checklist.md",
    "checklists/human_review_signoff_checklist.md",
    "checklists/release_hold_safety_checklist.md",
    "checklists/agent_handoff_checklist.md",
    "checklists/new_experiment_intake_checklist.md",
    "checklists/final_closeout_checklist.md",
]

REQUIRED_RECOVERY_DOCS = [
    "recovery/missing_quality_artifacts_recovery.md",
    "recovery/corrupted_json_recovery.md",
    "recovery/reproducibility_mismatch_recovery.md",
    "recovery/invalid_safety_flags_recovery.md",
    "recovery/missing_review_packet_recovery.md",
    "recovery/failed_full_suite_recovery.md",
    "recovery/untracked_external_state_recovery.md",
    "recovery/bad_commit_recovery.md",
    "recovery/restore_to_tags_recovery.md",
]

SAFETY_KEYWORDS = [
    "release_hold",
    "HOLD",
    "advisory_only",
    "no_live",
    "no_submit",
    "no_network",
    "human_review_required",
    "no_auto_promotion",
]

FORBIDDEN_APPROVAL_KEYWORDS = [
    "APPROVE_LIVE",
    "APPROVE_TESTNET_SUBMIT",
    "APPROVE_RUNTIME",
    "APPROVE_PLANNER_INTEGRATION",
    "auto_promote",
    "auto-promotion",
]

UNTRACKED_WARNING_KEYWORDS = [
    "untracked",
    "external state",
    "live_runner",
    "live_playbook",
    "testnet",
]


def check_file_exists(docs_root: Path, relative_path: str) -> bool:
    """Check if a doc file exists."""
    return (docs_root / relative_path).is_file()


def check_file_contains(filepath: Path, keywords: List[str]) -> Dict[str, bool]:
    """Check which keywords appear in a file."""
    if not filepath.is_file():
        return {k: False for k in keywords}
    text = filepath.read_text().lower()
    return {k: k.lower() in text for k in keywords}


def validate_required_docs(docs_root: Path) -> Dict[str, Any]:
    """Validate all required documentation exists."""
    missing = []
    found = []
    for rel in REQUIRED_OPERATOR_MANUALS + REQUIRED_RUNBOOKS + REQUIRED_CHECKLISTS + REQUIRED_RECOVERY_DOCS:
        if check_file_exists(docs_root, rel):
            found.append(rel)
        else:
            missing.append(rel)
    return {
        "valid": len(missing) == 0,
        "found": len(found),
        "missing": missing,
        "total_required": len(REQUIRED_OPERATOR_MANUALS) + len(REQUIRED_RUNBOOKS) + len(REQUIRED_CHECKLISTS) + len(REQUIRED_RECOVERY_DOCS),
    }


def validate_safety_statements(docs_root: Path) -> Dict[str, Any]:
    """Validate safety boundary statements exist in key docs."""
    key_docs = [
        "operator_manuals/offline_research_stack_safety_manual.md",
        "operator_manuals/offline_research_stack_operator_manual.md",
        "checklists/release_hold_safety_checklist.md",
    ]
    results = {}
    all_present = True
    for rel in key_docs:
        fp = docs_root / rel
        if fp.is_file():
            found = check_file_contains(fp, SAFETY_KEYWORDS)
            results[rel] = found
            if not all(found.values()):
                all_present = False
        else:
            results[rel] = {k: False for k in SAFETY_KEYWORDS}
            all_present = False
    return {"valid": all_present, "results": results}


def validate_no_forbidden_approvals(docs_root: Path) -> Dict[str, Any]:
    """Check that docs don't accidentally approve live/testnet/runtime.

    Only flags forbidden approval keywords that appear outside of
    forbidden/warning/safety context. Lines under headings containing
    'forbidden', 'safety', or 'never' are excluded.
    """
    violations = []
    forbidden_heading_context = (
        "forbidden", "safety", "never", "do not", "must not",
        "what not", "not to do", "prohibited", "blocked",
    )
    for rel in REQUIRED_OPERATOR_MANUALS + REQUIRED_RUNBOOKS:
        fp = docs_root / rel
        if fp.is_file():
            text = fp.read_text()
            lines = text.split("\n")
            in_forbidden_section = False
            for line_no, line in enumerate(lines, 1):
                ll = line.lower().strip()
                # Track section headings
                if ll.startswith("#"):
                    in_forbidden_section = any(
                        ctx in ll for ctx in forbidden_heading_context
                    )
                    continue
                if in_forbidden_section:
                    continue
                for kw in FORBIDDEN_APPROVAL_KEYWORDS:
                    if kw.lower() in ll:
                        if any(w in ll for w in [
                            "forbidden", "not", "never", "must not",
                            "do not", "no ", "without", "reject",
                            "blocked", "prohibited", "cannot",
                        ]):
                            continue
                        violations.append(f"{rel}:{line_no}: {kw}")
    return {"valid": len(violations) == 0, "violations": violations}


def validate_untracked_warning(docs_root: Path) -> Dict[str, Any]:
    """Check that operator manual includes untracked external state warning."""
    fp = docs_root / "operator_manuals/offline_research_stack_operator_manual.md"
    if not fp.is_file():
        return {"valid": False, "reason": "operator manual missing"}
    found = check_file_contains(fp, UNTRACKED_WARNING_KEYWORDS)
    return {"valid": any(found.values()), "found": found}


def run_full_governance_validation(docs_root: Path, release_hold: str = "HOLD") -> Dict[str, Any]:
    """Run full governance validation suite."""
    errors = []
    if release_hold != "HOLD":
        errors.append(f"release_hold must be HOLD, got {release_hold}")

    doc_check = validate_required_docs(docs_root)
    if not doc_check["valid"]:
        for m in doc_check["missing"]:
            errors.append(f"missing_doc: {m}")

    safety_check = validate_safety_statements(docs_root)
    if not safety_check["valid"]:
        errors.append("safety_statements_incomplete")

    approval_check = validate_no_forbidden_approvals(docs_root)
    if not approval_check["valid"]:
        for v in approval_check["violations"]:
            errors.append(f"forbidden_approval: {v}")

    untracked_check = validate_untracked_warning(docs_root)
    if not untracked_check["valid"]:
        errors.append("missing_untracked_external_state_warning")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "release_hold": release_hold,
        "doc_check": doc_check,
        "safety_check": safety_check["valid"],
        "approval_check": approval_check["valid"],
        "untracked_warning_check": untracked_check["valid"],
    }
