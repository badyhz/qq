"""Offline backtest bundle builder — pure functions, no I/O.

Assembles artifact descriptors and manifests for the historical OHLCV
backtest research bundle.  File I/O is handled by the CLI script only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# content hash (file path variant)
# ---------------------------------------------------------------------------

def compute_sha256(path: str | Path) -> str:
    """Compute SHA-256 hex digest of a file on disk.

    Parameters
    ----------
    path : str or Path
        Path to file.

    Returns
    -------
    str
        64-char hex digest.

    Raises
    ------
    FileNotFoundError
        If path does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for block in iter(lambda: fh.read(8192), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# manifest builder
# ---------------------------------------------------------------------------

def build_manifest(artifact_paths: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the bundle manifest from artifact descriptor list.

    Parameters
    ----------
    artifact_paths : list[dict]
        Each dict must have ``name`` (str), ``sha256`` (str),
        and ``size_bytes`` (int).

    Returns
    -------
    dict
        Manifest with safety flags and artifact inventory.
    """
    return {
        "release_hold": "HOLD",
        "no_live": True,
        "no_submit": True,
        "no_exchange": True,
        "generated_by": "offline_backtest_bundle_builder",
        "artifact_count": len(artifact_paths),
        "artifacts": list(artifact_paths),
    }


# ---------------------------------------------------------------------------
# bundle assembly
# ---------------------------------------------------------------------------

def build_backtest_bundle(
    output_dir: str | Path,
    artifacts_dict: dict[str, str],
) -> dict[str, Any]:
    """Build a backtest research bundle manifest from a dict of artifacts.

    Parameters
    ----------
    output_dir : str or Path
        The directory where artifacts are expected to reside (for size/hash).
    artifacts_dict : dict[str, str]
        Mapping of artifact name -> file path on disk.

    Returns
    -------
    dict
        Manifest dict with safety flags and artifact inventory.
    """
    descriptors: list[dict[str, Any]] = []
    for name in sorted(artifacts_dict):
        fpath = Path(artifacts_dict[name])
        if not fpath.exists():
            raise FileNotFoundError(f"Artifact not found: {fpath}")
        descriptors.append({
            "name": name,
            "sha256": compute_sha256(fpath),
            "size_bytes": fpath.stat().st_size,
        })
    return build_manifest(descriptors)
