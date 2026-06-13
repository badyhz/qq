"""Output router. Routes E2E output to isolated directories."""
from __future__ import annotations
import json, pathlib, shutil
from datetime import datetime, timezone

def route_output(base_dir: pathlib.Path, run_id: str, output_dir: pathlib.Path | None = None) -> pathlib.Path:
    """Create and return isolated output directory for a run."""
    if output_dir:
        run_dir = output_dir / run_id
    else:
        run_dir = base_dir / "runtime_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir

def copy_artifacts_to_run(src_runtime: pathlib.Path, run_dir: pathlib.Path) -> None:
    """Copy runtime artifacts to run directory."""
    for subdir in ("e2e", "shadow", "alerts", "operator", "testnet_sim", "research"):
        src = src_runtime / subdir
        if src.exists():
            dst = run_dir / subdir
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
