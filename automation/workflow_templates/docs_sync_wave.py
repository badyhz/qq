"""DOCS_SYNC_WAVE template."""
DOCS_SYNC_WAVE = {
    "name": "DOCS_SYNC_WAVE",
    "description": "Synchronize all docs to reflect current state.",
    "inputs": {
        "current_metrics": {"type": "dict", "required": True, "description": "TRUE_GUARDED, coverage, tests"},
        "doc_files": {"type": "list[str]", "required": True, "description": "Docs to update"},
        "batch_scripts": {"type": "list[str]", "required": True, "description": "New scripts to add to inventories"},
    },
    "outputs": {
        "updated_docs": {"type": "list[str]", "description": "Files updated"},
        "staleness_report": {"type": "dict", "description": "Fields changed per doc"},
    },
    "parallel_policy": {
        "mode": "DAG",
        "max_agents": 5,
        "rules": [
            "Independent writes to different files",
            "No two agents edit same doc",
            "Verify after each sync",
        ],
    },
    "validation_checklist": [
        "All stale counts updated",
        "All inventory lists complete",
        "All batch statuses correct",
        "All metrics consistent across docs",
    ],
    "stop_conditions": [
        "Doc count mismatch",
        "Missing inventory entry",
        "Inconsistent batch status",
    ],
    "anti_patterns": [
        "Edit same doc from multiple agents",
        "Skip verification after sync",
        "Assume counts without checking",
        "Forget to update Audit Snapshot",
    ],
}
