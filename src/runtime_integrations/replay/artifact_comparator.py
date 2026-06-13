"""Artifact comparator. Compares runtime artifacts across replay runs."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactComparison:
    artifact_name: str
    present_in_all_runs: bool
    schema_consistent: bool
    record_counts: tuple[int, ...]
    count_variation: int
    status: str  # STABLE, VARIABLE, MISSING

    def to_dict(self) -> dict:
        return {
            "artifact_name": self.artifact_name,
            "present_in_all_runs": self.present_in_all_runs,
            "schema_consistent": self.schema_consistent,
            "record_counts": list(self.record_counts),
            "count_variation": self.count_variation,
            "status": self.status,
        }


EXPECTED_ARTIFACTS = (
    "data/runtime/research/watchlist_evidence.jsonl",
    "data/runtime/shadow/signals.jsonl",
    "data/runtime/shadow/scorecard.json",
    "data/runtime/shadow/promotion_evidence.jsonl",
    "data/runtime/testnet_sim/order_intents.jsonl",
    "data/runtime/testnet_sim/order_lifecycle.jsonl",
    "data/runtime/testnet_sim/no_submit_evidence.jsonl",
    "data/runtime/alerts/alerts.jsonl",
    "data/runtime/alerts/feishu_dry_run_payloads.jsonl",
    "data/runtime/operator/system_state.json",
    "data/runtime/e2e/run_manifest.json",
    "reports/operator_dashboard.html",
    "reports/system_dry_run_e2e_report.md",
)


def _count_records(path: pathlib.Path) -> int:
    if not path.exists():
        return -1
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return 0
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return len(data)
        return 1
    except json.JSONDecodeError:
        return len([l for l in content.splitlines() if l.strip()])


def _extract_keys(path: pathlib.Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        content = path.read_text(encoding="utf-8").strip()
        first_line = content.splitlines()[0] if content else "{}"
        return set(json.loads(first_line).keys())
    except (json.JSONDecodeError, IndexError):
        return set()


def compare_artifacts(run_dirs: list[pathlib.Path]) -> list[ArtifactComparison]:
    """Compare artifacts across multiple run directories."""
    comparisons = []
    for artifact in EXPECTED_ARTIFACTS:
        counts = []
        all_present = True
        key_sets = []
        for run_dir in run_dirs:
            path = run_dir / artifact
            if not path.exists():
                all_present = False
                counts.append(-1)
            else:
                counts.append(_count_records(path))
                key_sets.append(_extract_keys(path))

        if not all_present:
            status = "MISSING"
            schema_consistent = False
        elif len(key_sets) > 1 and key_sets[0] and not all(ks == key_sets[0] for ks in key_sets):
            status = "VARIABLE"
            schema_consistent = False
        else:
            valid_counts = [c for c in counts if c >= 0]
            variation = max(valid_counts) - min(valid_counts) if valid_counts else 0
            status = "STABLE"
            schema_consistent = True

        valid_counts = tuple(c for c in counts if c >= 0)
        comparisons.append(ArtifactComparison(
            artifact_name=artifact,
            present_in_all_runs=all_present,
            schema_consistent=schema_consistent,
            record_counts=tuple(counts),
            count_variation=max(valid_counts) - min(valid_counts) if valid_counts else 0,
            status=status,
        ))

    return comparisons


def write_comparison(comparisons: list[ArtifactComparison], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([c.to_dict() for c in comparisons], indent=2),
        encoding="utf-8",
    )
