"""Split boundary hash — deterministic boundary hash capture.

Pure functions. No network.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Tuple


def compute_boundary_hash(
    split_id: str,
    train_range: Tuple[int, int],
    test_range: Tuple[int, int],
) -> str:
    """Compute deterministic boundary hash for a split."""
    raw = json.dumps({
        "split_id": split_id,
        "train_start": train_range[0],
        "train_end": train_range[1],
        "test_start": test_range[0],
        "test_end": test_range[1],
    }, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def compute_all_boundary_hashes(
    splits: List[Dict[str, Any]],
) -> Dict[str, str]:
    """Compute boundary hashes for all splits."""
    hashes = {}
    for s in splits:
        sid = s.get("split_id", "")
        train = (s.get("train_start", 0), s.get("train_end", 0))
        test = (s.get("test_start", 0), s.get("test_end", 0))
        hashes[sid] = compute_boundary_hash(sid, train, test)
    return hashes
