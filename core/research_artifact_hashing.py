"""Research artifact hashing — input/output artifact hashing.

Stable hashing. Allowlist for timestamp fields. No network.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple

TIMESTAMP_ALLOWLIST = ("generated_at", "created_at", "updated_at", "run_at")


def hash_file(path: Path) -> str:
    """Hash file contents with SHA-256."""
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_artifact_content(data: dict, exclude_timestamps: bool = True) -> str:
    """Hash artifact content with stable JSON, excluding timestamp fields."""
    filtered = data
    if exclude_timestamps:
        filtered = _strip_timestamps(data)
    stable = json.dumps(filtered, sort_keys=True, indent=2, default=str)
    return hashlib.sha256(stable.encode()).hexdigest()


def _strip_timestamps(obj):
    """Recursively strip timestamp fields from dict."""
    if isinstance(obj, dict):
        return {k: _strip_timestamps(v) for k, v in obj.items() if k not in TIMESTAMP_ALLOWLIST}
    elif isinstance(obj, list):
        return [_strip_timestamps(item) for item in obj]
    return obj


def compute_artifact_hashes(
    directory: Path,
    artifact_names: Tuple[str, ...],
) -> Dict[str, str]:
    """Compute hashes for named artifacts in directory."""
    hashes = {}
    for name in sorted(artifact_names):
        p = directory / name
        if p.exists():
            if p.suffix == ".json":
                try:
                    data = json.loads(p.read_text())
                    hashes[name] = hash_artifact_content(data)
                    continue
                except (json.JSONDecodeError, ValueError):
                    pass
            hashes[name] = hash_file(p)
    return hashes


def compare_hashes(
    left: Dict[str, str],
    right: Dict[str, str],
    allowlist: Tuple[str, ...] = TIMESTAMP_ALLOWLIST,
) -> Tuple[Dict[str, str], Tuple[str, ...]]:
    """Compare two hash sets. Returns (differences, missing)."""
    diffs = {}
    missing = []

    all_keys = set(list(left.keys()) + list(right.keys()))
    for key in sorted(all_keys):
        if key not in left:
            missing.append(f"LEFT_MISSING:{key}")
        elif key not in right:
            missing.append(f"RIGHT_MISSING:{key}")
        elif left[key] != right[key]:
            # Check if this is a timestamp-only artifact
            is_timestamp_artifact = any(al in key for al in allowlist)
            if not is_timestamp_artifact:
                diffs[key] = {"left": left[key], "right": right[key]}

    return diffs, tuple(missing)
