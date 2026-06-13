#!/usr/bin/env python3
"""T65001 — Runtime Replay Harness."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.runtime_integrations.replay.replay_harness import run_replay, write_manifest, write_report
from src.runtime_integrations.replay.artifact_comparator import compare_artifacts, write_comparison

def main():
    data_dir = ROOT / "data"
    reports_dir = ROOT / "reports"
    num_runs = 3
    manifest = run_replay(num_runs, data_dir, reports_dir)
    write_manifest(manifest, data_dir / "runtime" / "replay" / "replay_manifest.json")
    write_report(manifest, reports_dir / "runtime_replay_harness_report.md")
    print(f"Replay: {manifest.total_runs} runs, all_passed={manifest.all_passed}")

if __name__ == "__main__":
    main()
