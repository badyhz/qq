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

VALID_SPLIT_MODES = ("rolling", "anchored", "walk_forward", "expanding")

REQUIRED_CATEGORIES = (
    "baseline",
    "strategy_specific",
    "symbol_universe",
    "timeframe",
    "split_mode",
    "search_budget",
    "robustness",
    "negative_control",
    "bootstrap",
    "regime",
    "portfolio_risk",
    "reproducibility",
    "report_quality",
    "human_review",
    "smoke_test",
    "stress_test",
    "sparse_signal",
    "noisy_fixture",
    "adverse_fixture",
    "comparison_analytics",
)

EXPERIMENT_LIBRARY_VERSION = "2.0.0"


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
        if sf.get("no_network") is not True:
            errors.append("no_network must be True")

    # Validate field types and values
    if "strategy_set" in experiment:
        ss = experiment["strategy_set"]
        if not isinstance(ss, list) or len(ss) == 0:
            errors.append("strategy_set must be non-empty list")

    if "symbols" in experiment:
        syms = experiment["symbols"]
        if not isinstance(syms, list) or len(syms) == 0:
            errors.append("symbols must be non-empty list")

    if "timeframes" in experiment:
        tfs = experiment["timeframes"]
        if not isinstance(tfs, list) or len(tfs) == 0:
            errors.append("timeframes must be non-empty list")

    if "split_mode" in experiment:
        sm = experiment["split_mode"]
        if sm not in VALID_SPLIT_MODES:
            errors.append(f"invalid_split_mode: {sm} (valid: {VALID_SPLIT_MODES})")

    if "search_budget" in experiment:
        sb = experiment["search_budget"]
        if not isinstance(sb, (int, float)) or sb <= 0:
            errors.append("search_budget must be positive number")

    if "chunk_size" in experiment:
        cs = experiment["chunk_size"]
        if not isinstance(cs, (int, float)) or cs <= 0:
            errors.append("chunk_size must be positive number")

    if "deterministic_seed" in experiment:
        ds = experiment["deterministic_seed"]
        if ds is None:
            errors.append("deterministic_seed must not be None")
        elif not isinstance(ds, (int, float)):
            errors.append("deterministic_seed must be numeric")

    if "expected_artifact_set" in experiment:
        eas = experiment["expected_artifact_set"]
        if not isinstance(eas, list) or len(eas) == 0:
            errors.append("expected_artifact_set must be non-empty list")

    if "expected_review_path" in experiment:
        erp = experiment["expected_review_path"]
        if not isinstance(erp, str) or len(erp) == 0:
            errors.append("expected_review_path must be non-empty string")

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
        "version": "2.0.0",
        "generated_by": "offline_research_experiment_library",
        "count": len(entries),
        "entries": sorted(entries, key=lambda e: e["experiment_id"]),
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
    }
