"""Feishu review packet. Assembles review data without sending."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class ReviewPacket:
    run_id: str
    artifacts: tuple[str, ...]
    summary: str
    def to_dict(self) -> dict:
        return {"run_id": self.run_id, "artifacts": list(self.artifacts), "summary": self.summary}

def build_review_packet(run_dir: pathlib.Path) -> ReviewPacket:
    manifest_path = run_dir / "run_manifest.json"
    run_id = "unknown"
    if manifest_path.exists():
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        run_id = m.get("run_id", "unknown")
    artifacts = []
    for p in sorted(run_dir.rglob("*.json")):
        artifacts.append(str(p.relative_to(run_dir)))
    for p in sorted(run_dir.rglob("*.jsonl")):
        artifacts.append(str(p.relative_to(run_dir)))
    for p in sorted(run_dir.rglob("*.html")):
        artifacts.append(str(p.relative_to(run_dir)))
    for p in sorted(run_dir.rglob("*.md")):
        artifacts.append(str(p.relative_to(run_dir)))
    summary = f"Review packet for {run_id}: {len(artifacts)} artifacts"
    return ReviewPacket(run_id, tuple(artifacts), summary)

def write_packet(packet: ReviewPacket, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet.to_dict(), indent=2), encoding="utf-8")
