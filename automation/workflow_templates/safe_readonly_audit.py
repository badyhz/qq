"""SAFE_READONLY_AUDIT template."""
SAFE_READONLY_AUDIT = {
    "name": "SAFE_READONLY_AUDIT",
    "description": "Audit non-frozen scripts for guard eligibility.",
    "inputs": {
        "candidate_scripts": {"type": "list[str]", "required": True, "description": "Scripts to audit"},
        "frozen_files": {"type": "list[str]", "required": True, "description": "Files that must not be modified"},
        "guard_contract": {"type": "dict", "required": True, "description": "Guard function definition"},
    },
    "outputs": {
        "eligible": {"type": "list[str]", "description": "Scripts approved for guard injection"},
        "not_eligible": {"type": "list[str]", "description": "Scripts rejected"},
        "risk_assessment": {"type": "dict", "description": "Risk per script"},
    },
    "parallel_policy": {
        "mode": "DAG",
        "max_agents": 5,
        "rules": [
            "Independent reads: unlimited",
            "Different files: parallel safe",
            "Same file: sequential",
        ],
    },
    "validation_checklist": [
        "Script exists in scripts/ directory",
        "Has main() function",
        "Not in frozen list",
        "No high-risk imports",
        "Not already guarded",
    ],
    "stop_conditions": [
        "Frozen file detected in candidates",
        "Script has high-risk imports",
        "Script already guarded",
    ],
    "anti_patterns": [
        "Skip frozen exclusion check",
        "Assume scripts are safe without reading",
        "Batch too many scripts (>5)",
    ],
    "tasks": [
        {"id": "scan_candidate_scripts", "deps": []},
        {"id": "check_frozen_exclusion", "deps": ["scan_candidate_scripts"]},
        {"id": "classify_risk_level", "deps": ["check_frozen_exclusion"]},
        {"id": "verify_guard_eligibility", "deps": ["classify_risk_level"]},
        {"id": "produce_audit_report", "deps": ["verify_guard_eligibility"]},
    ],
}
