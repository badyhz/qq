"""EXECUTION_GUARD_DOCS_SYNC template — sync docs after guard injection."""
EXECUTION_GUARD_DOCS_SYNC = {
    "name": "EXECUTION_GUARD_DOCS_SYNC",
    "description": "Synchronize documentation, dashboard, and metrics after guard injection batch.",
    "mode": "DAG",
    "inputs": {
        "guarded_scripts": {"type": "list[str]", "required": True, "description": "Scripts with guard injected"},
        "batch_id": {"type": "str", "required": True, "description": "Batch identifier"},
    },
    "outputs": {
        "sync_report": {"type": "dict", "description": "Sync results per doc"},
    },
    "parallel_policy": {
        "mode": "DAG",
        "max_agents": 3,
        "rules": [
            "Doc updates are independent: parallel",
            "Dashboard and matrix sync: parallel",
            "Final verification: sequential",
        ],
    },
    "tasks": [
        {"id": "sync_feature_matrix", "deps": []},
        {"id": "sync_guard_dashboard", "deps": []},
        {"id": "update_metrics", "deps": []},
        {"id": "verify_doc_consistency", "deps": ["sync_feature_matrix", "sync_guard_dashboard", "update_metrics"]},
    ],
    "validation_checklist": [
        "Feature matrix reflects new guarded scripts",
        "Dashboard shows updated guard count",
        "Metrics are consistent across docs",
        "No stale entries in matrix",
    ],
    "stop_conditions": [
        "Doc inconsistency detected",
        "Dashboard render failure",
    ],
    "anti_patterns": [
        "Skip verification step",
        "Update docs without batch_id traceability",
    ],
    "safety_policy": {
        "allowed_categories": ["READONLY", "AUDIT", "DOCS"],
        "blocked_categories": ["SUBMIT", "CANCEL", "FLATTEN", "LIVE_EXECUTION"],
    },
}
