"""Artifact manifest. Lists and hashes all runtime artifacts."""
from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ArtifactEntry:
    path: str
    size_bytes: int
    sha256: str
    parseable: bool
    record_count: int
    stale: bool

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "parseable": self.parseable,
            "record_count": self.record_count,
            "stale": self.stale,
        }


def _hash_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _count_records(path: pathlib.Path) -> int:
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return 0
        data = json.loads(content)
        if isinstance(data, list):
            return len(data)
        return 1
    except (json.JSONDecodeError, UnicodeDecodeError):
        lines = [l for l in content.splitlines() if l.strip()]
        return len(lines)


def _is_parseable(path: pathlib.Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return True
        if path.suffix == ".json":
            json.loads(content)
        elif path.suffix == ".jsonl":
            # Try whole-file JSON first (some files are JSON arrays written to .jsonl)
            try:
                json.loads(content)
            except json.JSONDecodeError:
                # Fall back to line-by-line JSONL
                for line in content.splitlines():
                    if line.strip():
                        json.loads(line)
        elif path.suffix == ".html":
            return len(content) > 0
        return True
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False


EXPECTED_ARTIFACTS = (
    "data/runtime/research/watchlist_evidence.jsonl",
    "data/runtime/research/research_source_status.json",
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


def scan_artifacts(root: pathlib.Path) -> list[ArtifactEntry]:
    """Scan and catalog all expected runtime artifacts."""
    entries = []
    now = datetime.now(timezone.utc)
    for rel in EXPECTED_ARTIFACTS:
        path = root / rel
        if path.exists():
            stat = path.stat()
            entries.append(ArtifactEntry(
                path=rel,
                size_bytes=stat.st_size,
                sha256=_hash_file(path),
                parseable=_is_parseable(path),
                record_count=_count_records(path) if path.suffix in (".json", ".jsonl") else -1,
                stale=False,
            ))
        else:
            entries.append(ArtifactEntry(
                path=rel,
                size_bytes=0,
                sha256="",
                parseable=False,
                record_count=-1,
                stale=True,
            ))
    return entries


def write_manifest(entries: list[ArtifactEntry], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(json.dumps(e.to_dict()) for e in entries) + ("\n" if entries else ""),
        encoding="utf-8",
    )


def write_hashes(entries: list[ArtifactEntry], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    hashes = {e.path: e.sha256 for e in entries if e.sha256}
    out_path.write_text(json.dumps(hashes, indent=2), encoding="utf-8")
