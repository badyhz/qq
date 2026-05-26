"""GUARD_INJECTION_BATCH template."""
GUARD_INJECTION_BATCH = {
    "name": "GUARD_INJECTION_BATCH",
    "description": "Inject guard contract into 5 scripts per batch.",
    "inputs": {
        "scripts": {"type": "list[str]", "required": True, "description": "5 approved scripts"},
        "guard_contract": {"type": "dict", "required": True, "description": "Guard function to inject"},
        "test_pattern": {"type": "str", "required": True, "description": "Test file template"},
    },
    "outputs": {
        "guarded_scripts": {"type": "list[str]", "description": "Scripts with guard injected"},
        "test_files": {"type": "list[str]", "description": "Created test files"},
        "test_results": {"type": "dict", "description": "Test pass/fail counts"},
    },
    "parallel_policy": {
        "mode": "QUEUE",
        "max_agents": 1,
        "rules": [
            "One batch at a time",
            "Inject → test → sync sequence",
            "Each step validates before next",
        ],
    },
    "validation_checklist": [
        "Guard is first 2 lines in main()",
        "No high-risk imports added",
        "6/6 tests pass per script",
        "No regression in baseline",
    ],
    "stop_conditions": [
        "Test failure",
        "Guard placement error",
        "Regression detected",
        "Frozen file conflict",
    ],
    "anti_patterns": [
        "Inject guard inside argparse logic",
        "Skip regression testing",
        "Batch more than 5 scripts",
        "Forget to check existing imports",
    ],
}
