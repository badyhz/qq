"""ENGINEERING_CLOSEOUT template."""
ENGINEERING_CLOSEOUT = {
    "name": "ENGINEERING_CLOSEOUT",
    "description": "Standardized phase/milestone closure with git integrity.",
    "inputs": {
        "phase_name": {"type": "str", "required": True, "description": "Phase identifier"},
        "closure_commit_message": {"type": "str", "required": True, "description": "Commit message"},
        "files_to_commit": {"type": "list[str]", "required": True, "description": "Files to stage"},
    },
    "outputs": {
        "closure_commit": {"type": "str", "description": "Commit hash"},
        "closure_tag": {"type": "str", "description": "Tag name"},
        "verification": {"type": "dict", "description": "Integrity check results"},
    },
    "parallel_policy": {
        "mode": "CLOSEOUT",
        "max_agents": 1,
        "rules": [
            "Sequential: verify → stage → commit → tag → verify",
            "No parallel file operations",
            "Tag created after commit only",
        ],
    },
    "validation_checklist": [
        "Inside git repo",
        "Clean tree (except frozen/junk)",
        "No frozen files staged",
        "Commit created successfully",
        "Tag points to HEAD",
        "No frozen files in commit",
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
        "Skip tag target verification",
    ],
}
