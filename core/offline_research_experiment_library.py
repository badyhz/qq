"""Offline research experiment library — deterministic experiment definitions.

No network. No exchange. No runtime. No planner. Advisory only.
release_hold remains HOLD. Human review required.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

REQUIRED_EXPERIMENT_FIELDS = (
    "experiment_id",
    "label",
    "description",
    "strategy_set",
    "symbols",
    "timeframes",
    "split_mode",
    "search_budget",
    "chunk_size",
    "deterministic_seed",
    "expected_artifact_set",
    "safety_flags",
    "allowed_commands",
    "forbidden_commands",
    "expected_review_path",
    "notes",
)

REQUIRED_SAFETY_FLAGS = (
    "release_hold",
    "advisory_only",
    "human_review_required",
    "no_live",
    "no_submit",
    "no_exchange",
    "no_network",
    "no_runtime_integration",
    "no_planner_integration",
)

FORBIDDEN_LIVE_STRINGS = (
    "live_trading",
    "testnet_submit",
    "order_placement",
    "order_cancel",
    "order_flatten",
    "runtime_activation",
    "planner_integration",
    "auto_promote",
    "APPROVE_LIVE",
    "APPROVE_TESTNET",
    "APPROVE_RUNTIME",
    "APPROVE_PLANNER",
)

FORBIDDEN_COMMANDS = (
    "submit_order",
    "cancel_order",
    "flatten_position",
    "place_order",
    "testnet_submit",
    "live_trading",
    "runtime_start",
    "planner_run",
    "exchange_connect",
    "binance_client",
)


def load_experiment_catalog(catalog_path: Path) -> Dict[str, Any]:
    """Load experiment catalog from JSON file."""
    with open(catalog_path) as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Catalog must be a JSON object")
    if "experiments" not in data:
        raise ValueError("Catalog missing 'experiments' key")
    if not isinstance(data["experiments"], list):
        raise ValueError("'experiments' must be a list")
    return data


def validate_experiment(experiment: Dict[str, Any]) -> List[str]:
    """Validate a single experiment definition. Returns list of errors."""
    errors = []
    for field in REQUIRED_EXPERIMENT_FIELDS:
        if field not in experiment:
            errors.append(f"missing_required_field: {field}")

    if "safety_flags" in experiment:
        sf = experiment["safety_flags"]
        for flag in REQUIRED_SAFETY_FLAGS:
            if flag not in sf:
                errors.append(f"missing_safety_flag: {flag}")
        if sf.get("release_hold") != "HOLD":
            errors.append("release_hold must be HOLD")
        if sf.get("advisory_only") is not True:
            errors.append("advisory_only must be True")
        if sf.get("human_review_required") is not True:
            errors.append("human_review_required must be True")

    forbidden_found = check_forbidden_strings(experiment)
    errors.extend(forbidden_found)

    return errors


def check_forbidden_strings(experiment: Dict[str, Any]) -> List[str]:
    """Check for forbidden live/testnet/runtime strings in experiment.

    Only checks fields that should NOT contain these strings:
    notes, label, description. Does NOT check forbidden_commands (which
    legitimately lists these strings as things to forbid).
    """
    errors = []
    check_fields = ["notes", "label", "description"]
    for field in check_fields:
        value = str(experiment.get(field, "")).lower()
        for fb in FORBIDDEN_LIVE_STRINGS:
            if fb.lower() in value:
                errors.append(f"forbidden_string_detected: {fb} (in {field})")
    return errors


def validate_forbidden_commands(experiment: Dict[str, Any]) -> List[str]:
    """Check allowed_commands do not contain forbidden commands."""
    errors = []
    allowed = [c.lower() for c in experiment.get("allowed_commands", [])]
    for fc in FORBIDDEN_COMMANDS:
        if fc.lower() in allowed:
            errors.append(f"forbidden_command_in_allowed: {fc}")
    return errors


def compute_experiment_hash(experiment: Dict[str, Any]) -> str:
    """Compute deterministic hash of experiment definition."""
    canonical = json.dumps(experiment, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def build_experiment_manifest(experiments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build manifest from list of validated experiments."""
    entries = []
    for exp in experiments:
        entries.append({
            "experiment_id": exp["experiment_id"],
            "label": exp["label"],
            "hash": compute_experiment_hash(exp),
            "safety_flags": exp["safety_flags"],
        })
    return {
        "version": "1.0.0",
        "generated_by": "offline_research_experiment_library",
        "count": len(entries),
        "entries": entries,
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
    }
