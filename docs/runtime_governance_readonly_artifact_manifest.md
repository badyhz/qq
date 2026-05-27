# Runtime Governance Read-Only Artifact Manifest

## Purpose

Static manifest for T826-T853 governance artifacts. Three artifacts per task (core, test, doc), 84 total.

## Usage

```python
from core.runtime_governance_readonly_artifact_manifest import (
    build_readonly_artifact_manifest,
    readonly_artifact_manifest_to_dict,
    readonly_artifact_manifest_to_markdown,
    summarize_readonly_artifact_manifest,
)

artifacts = build_readonly_artifact_manifest()
summary = summarize_readonly_artifact_manifest(artifacts)
# summary["total"] == 84
```

## Constraints

- Pure, deterministic, no I/O
- No timestamps, no random values
- All dataclasses frozen
