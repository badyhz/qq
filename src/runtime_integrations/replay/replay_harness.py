"""Replay harness. Runs E2E multiple times and compares output stability."""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.runtime_integrations.e2e.system_dry_run_e2e import run_e2e


@dataclass(frozen=True)
class ReplayResult:
    run_index: int
    run_id: str
    status: str
    steps_completed: int
    errors: int

    def to_dict(self) -> dict:
        return {
            "run_index": self.run_index,
            "run_id": self.run_id,
            "status": self.status,
            "steps_completed": self.steps_completed,
            "errors": self.errors,
        }


@dataclass(frozen=True)
class ReplayManifest:
    manifest_id: str
    total_runs: int
    all_passed: bool
    results: tuple[ReplayResult, ...]
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "manifest_id": self.manifest_id,
            "total_runs": self.total_runs,
            "all_passed": self.all_passed,
            "results": [r.to_dict() for r in self.results],
            "timestamp": self.timestamp,
        }


def run_replay(num_runs: int, data_dir: pathlib.Path, reports_dir: pathlib.Path) -> ReplayManifest:
    """Run E2E num_runs times in isolated temp directories."""
    results = []
    now = datetime.now(timezone.utc).isoformat()

    for i in range(num_runs):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            run_data = tmp / "data"
            run_reports = tmp / "reports"
            run_data.mkdir()
            run_reports.mkdir()

            # Create fixture
            x_dir = run_data / "x_exports"
            x_dir.mkdir(parents=True)
            fixture = '{"tickers": ["BTC", "ETH", "SOL"], "timestamp": "2026-06-01", "source_file": "test.md"}\n'
            (x_dir / "test.jsonl").write_text(fixture, encoding="utf-8")

            result = run_e2e(run_data, run_reports)
            results.append(ReplayResult(
                run_index=i,
                run_id=result.get("run_id", "unknown"),
                status=result.get("status", "UNKNOWN"),
                steps_completed=len(result.get("steps_completed", [])),
                errors=len(result.get("errors", [])),
            ))

    all_passed = all(r.status == "SYSTEM_DRY_RUN_E2E_PASS" for r in results)
    return ReplayManifest(
        manifest_id=f"replay_{now.replace(':', '').replace('-', '')[:20]}",
        total_runs=num_runs,
        all_passed=all_passed,
        results=tuple(results),
        timestamp=now,
    )


def write_manifest(manifest: ReplayManifest, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")


def write_report(manifest: ReplayManifest, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Runtime Replay Harness Report",
        "",
        f"**Total runs:** {manifest.total_runs}",
        f"**All passed:** {manifest.all_passed}",
        "",
        "## Results",
        "",
        "| Run | Run ID | Status | Steps | Errors |",
        "|-----|--------|--------|-------|--------|",
    ]
    for r in manifest.results:
        lines.append(f"| {r.run_index} | {r.run_id[:20]}... | {r.status} | {r.steps_completed} | {r.errors} |")
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
