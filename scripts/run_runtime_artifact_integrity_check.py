#!/usr/bin/env python3
"""T69501 — Runtime Artifact Integrity Check."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.runtime_integrations.artifacts.artifact_manifest import scan_artifacts, write_manifest, write_hashes
from src.runtime_integrations.artifacts.artifact_validator import validate
from src.runtime_integrations.artifacts.artifact_retention_policy import write_policy

def main():
    entries = scan_artifacts(ROOT)
    write_manifest(entries, ROOT / "data" / "runtime" / "artifacts" / "artifact_manifest.jsonl")
    write_hashes(entries, ROOT / "data" / "runtime" / "artifacts" / "artifact_hashes.json")
    write_policy(ROOT / "reports" / "runtime_artifact_retention_policy.md")
    result = validate(entries)
    print(f"Artifacts: present={result.present}, missing={result.missing}, all_valid={result.all_valid}")

if __name__ == "__main__":
    main()
