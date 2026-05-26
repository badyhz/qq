"""QUANT_CLOSEOUT_PIPELINE template — quant workflow phase closure."""
QUANT_CLOSEOUT_PIPELINE = {
    "name": "QUANT_CLOSEOUT_PIPELINE",
    "description": "Close out a quant workflow phase: verify, document, commit, tag.",
    "mode": "QUEUE",
    "inputs": {
        "phase_name": {"type": "str", "required": True, "description": "Phase identifier"},
        "commit_message": {"type": "str", "required": True, "description": "Commit message"},
        "files_to_commit": {"type": "list[str]", "required": True, "description": "Files to stage"},
    },
    "outputs": {
        "commit_hash": {"type": "str", "description": "Git commit hash"},
        "tag_name": {"type": "str", "description": "Git tag"},
    },
    "parallel_policy": {
        "mode": "QUEUE",
        "max_agents": 1,
        "rules": [
            "Sequential: verify → stage → commit → tag → verify",
            "No parallel file operations",
            "Tag created after commit only",
        ],
    },
    "tasks": [
        {"id": "verify_clean_tree", "deps": []},
        {"id": "check_frozen_exclusion", "deps": ["verify_clean_tree"]},
        {"id": "stage_files", "deps": ["check_frozen_exclusion"]},
        {"id": "commit", "deps": ["stage_files"]},
        {"id": "tag_phase", "deps": ["commit"]},
        {"id": "verify_closeout", "deps": ["tag_phase"]},
    ],
    "validation_checklist": [
        "Clean git tree (except allowed untracked)",
        "No frozen files staged",
        "Commit created successfully",
        "Tag points to HEAD",
        "Closeout verification passes",
    ],
    "stop_conditions": [
        "Frozen file detected in staging",
        "Tag already exists",
        "Commit fails",
        "Verification failure",
    ],
    "anti_patterns": [
        "Use git add .",
        "Tag before commit",
        "Skip frozen exclusion check",
    ],
    "safety_policy": {
        "allowed_categories": ["READONLY", "AUDIT", "DOCS", "CLOSEOUT"],
        "blocked_categories": ["SUBMIT", "CANCEL", "FLATTEN", "LIVE_EXECUTION"],
    },
}
