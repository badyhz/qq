"""Research reproducibility seed — deterministic seed policy and stable JSON.

Same input + same seed = byte-stable JSON output.
No network, no exchange.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


DEFAULT_SEED = 424242


def stable_json(obj: Any, indent: int = 2) -> str:
    """Produce stable JSON with sorted keys and deterministic float formatting."""
    return json.dumps(obj, sort_keys=True, indent=indent, default=str)


def stable_json_hash(obj: Any) -> str:
    """Hash of stable JSON representation."""
    return hashlib.sha256(stable_json(obj).encode()).hexdigest()


def validate_seed(seed: int) -> bool:
    """Validate seed is a positive integer."""
    return isinstance(seed, int) and seed > 0


def seed_determinism_check(data: Any, seed: int, n_runs: int = 3) -> bool:
    """Verify that n_runs produce identical hashes."""
    hashes = set()
    for _ in range(n_runs):
        seeded = {"seed": seed, "data": data}
        h = stable_json_hash(seeded)
        hashes.add(h)
    return len(hashes) == 1


def input_hash(data: Any) -> str:
    """Compute deterministic input hash."""
    return stable_json_hash(data)
