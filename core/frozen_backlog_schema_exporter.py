"""T1801 - Frozen Backlog Review JSON Schema Exporter.

Pure functions that produce JSON schema dicts for each model type.
No I/O. No timestamps. No network.
"""
from __future__ import annotations


def export_report_schema() -> dict[str, object]:
    """JSON schema for frozen backlog review report. Pure function."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "FrozenBacklogReviewReport",
        "description": "Frozen backlog review report with summary and records.",
        "type": "object",
        "required": ["summary", "records"],
        "properties": {
            "summary": {
                "$ref": "#/definitions/FrozenBacklogReportSummary",
            },
            "records": {
                "type": "array",
                "items": {"$ref": "#/definitions/FrozenBacklogReportRecord"},
            },
        },
        "definitions": {
            "FrozenBacklogReportSummary": {
                "type": "object",
                "required": [
                    "summary_id",
                    "total_files",
                    "high_risk_count",
                    "medium_risk_count",
                    "release_hold",
                    "no_live",
                    "no_submit",
                    "no_exchange",
                    "no_runtime_integration",
                    "no_planner_integration",
                ],
                "properties": {
                    "summary_id": {"type": "string"},
                    "total_files": {"type": "integer"},
                    "high_risk_count": {"type": "integer"},
                    "medium_risk_count": {"type": "integer"},
                    "release_hold": {"type": "string", "const": "HOLD"},
                    "no_live": {"type": "boolean", "const": True},
                    "no_submit": {"type": "boolean", "const": True},
                    "no_exchange": {"type": "boolean", "const": True},
                    "no_runtime_integration": {"type": "boolean", "const": True},
                    "no_planner_integration": {"type": "boolean", "const": True},
                },
                "additionalProperties": False,
            },
            "FrozenBacklogReportRecord": {
                "type": "object",
                "required": [
                    "record_id",
                    "file_path",
                    "risk_class",
                    "category",
                    "allowed_actions",
                    "forbidden_actions",
                    "required_evidence",
                    "readiness_score",
                    "unlock_recommendation",
                    "release_hold",
                ],
                "properties": {
                    "record_id": {"type": "string"},
                    "file_path": {"type": "string"},
                    "risk_class": {"type": "string", "enum": ["HIGH", "MEDIUM"]},
                    "category": {
                        "type": "string",
                        "enum": [
                            "LIVE_RUNNER",
                            "LIVE_PLAYBOOK",
                            "SUBMIT",
                            "TESTNET_SMOKE",
                            "FLATTEN",
                            "REPLAY_SUBMIT",
                            "OPERATIONAL_SHADOW",
                            "VERIFICATION",
                        ],
                    },
                    "allowed_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "forbidden_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "required_evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "readiness_score": {"type": "number"},
                    "unlock_recommendation": {
                        "type": "string",
                        "enum": ["HOLD", "PROMOTE", "DEFER", "REJECT"],
                    },
                    "release_hold": {"type": "string", "const": "HOLD"},
                },
                "additionalProperties": False,
            },
        },
    }


def export_snapshot_schema() -> dict[str, object]:
    """JSON schema for frozen backlog snapshot. Pure function."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "FrozenBacklogSnapshot",
        "description": "Immutable snapshot of a frozen backlog report.",
        "type": "object",
        "required": ["snapshot_id", "report_data", "created_at_iso", "version"],
        "properties": {
            "snapshot_id": {"type": "string"},
            "report_data": {"$ref": "#/definitions/ReportData"},
            "created_at_iso": {"type": "string"},
            "version": {"type": "string"},
        },
        "definitions": {
            "ReportData": {
                "type": "object",
                "required": ["summary", "records"],
                "properties": {
                    "summary": {"type": "object"},
                    "records": {"type": "array"},
                },
            },
        },
    }


def export_diff_schema() -> dict[str, object]:
    """JSON schema for frozen backlog diff. Pure function."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "FrozenBacklogDiff",
        "description": "Diff between two frozen backlog report snapshots.",
        "type": "object",
        "required": [
            "diff_id",
            "before_snapshot_id",
            "after_snapshot_id",
            "added_files",
            "removed_files",
            "risk_class_changes",
            "category_changes",
            "recommendation_changes",
            "safety_flag_changes",
            "hold_changes",
        ],
        "properties": {
            "diff_id": {"type": "string"},
            "before_snapshot_id": {"type": "string"},
            "after_snapshot_id": {"type": "string"},
            "added_files": {"type": "array", "items": {"type": "string"}},
            "removed_files": {"type": "array", "items": {"type": "string"}},
            "risk_class_changes": {
                "type": "array",
                "items": {"$ref": "#/definitions/FrozenDiffChange"},
            },
            "category_changes": {
                "type": "array",
                "items": {"$ref": "#/definitions/FrozenDiffChange"},
            },
            "recommendation_changes": {
                "type": "array",
                "items": {"$ref": "#/definitions/FrozenDiffChange"},
            },
            "safety_flag_changes": {
                "type": "array",
                "items": {"$ref": "#/definitions/FrozenDiffChange"},
            },
            "hold_changes": {
                "type": "array",
                "items": {"$ref": "#/definitions/FrozenDiffChange"},
            },
        },
        "definitions": {
            "FrozenDiffChange": {
                "type": "object",
                "required": ["file_path", "field_name", "old_value", "new_value"],
                "properties": {
                    "file_path": {"type": "string"},
                    "field_name": {"type": "string"},
                    "old_value": {},
                    "new_value": {},
                },
                "additionalProperties": False,
            },
        },
    }


def export_verdict_schema() -> dict[str, object]:
    """JSON schema for frozen backlog verdict. Pure function."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "FrozenBacklogVerdict",
        "description": "Verdict from a frozen backlog review.",
        "type": "object",
        "required": ["verdict", "notes", "changed_fields", "risk_level"],
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["PASS", "PARTIAL", "FAIL"],
            },
            "notes": {"type": "string"},
            "changed_fields": {
                "type": "array",
                "items": {"type": "string"},
            },
            "risk_level": {
                "type": "string",
                "enum": ["SAFE", "CAUTION", "CRITICAL"],
            },
        },
        "additionalProperties": False,
    }


def export_audit_schema() -> dict[str, object]:
    """JSON schema for frozen backlog audit output. Pure function."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "FrozenBacklogAudit",
        "description": "Audit record for frozen backlog review.",
        "type": "object",
        "required": [
            "audit_id",
            "validation_result",
            "diff_summary",
            "verdict",
            "snapshot_ids",
        ],
        "properties": {
            "audit_id": {"type": "string"},
            "validation_result": {
                "type": "object",
                "required": [
                    "is_valid",
                    "checks_passed",
                    "checks_failed",
                    "error_message",
                ],
                "properties": {
                    "is_valid": {"type": "boolean"},
                    "checks_passed": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "checks_failed": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "error_message": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "diff_summary": {
                "type": "object",
                "required": [
                    "added_files",
                    "removed_files",
                    "total_changes",
                ],
                "properties": {
                    "added_files": {"type": "integer"},
                    "removed_files": {"type": "integer"},
                    "total_changes": {"type": "integer"},
                },
                "additionalProperties": False,
            },
            "verdict": {"$ref": "#/definitions/VerdictRef"},
            "snapshot_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "definitions": {
            "VerdictRef": {
                "type": "object",
                "required": ["verdict", "notes", "changed_fields", "risk_level"],
                "properties": {
                    "verdict": {
                        "type": "string",
                        "enum": ["PASS", "PARTIAL", "FAIL"],
                    },
                    "notes": {"type": "string"},
                    "changed_fields": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "risk_level": {
                        "type": "string",
                        "enum": ["SAFE", "CAUTION", "CRITICAL"],
                    },
                },
                "additionalProperties": False,
            },
        },
    }
