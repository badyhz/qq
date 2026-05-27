# T788-T789 — Governance Failure Reporting Stack

**Date:** 2026-05-27
**Status:** PASS

## Stack

| Layer | Module | Role |
|-------|--------|------|
| Taxonomy | `core/governance_failure_taxonomy.py` | Classify failures into categories/severities |
| Report | `core/governance_failure_report.py` | Build structured reports with verdict |
| Snapshot | `core/governance_failure_snapshot.py` | Compare markdown for deterministic diffs |
| Packet | `core/governance_failure_regression_packet.py` | Combine report + snapshot into regression packet |

## Final Verdict Rules

| Report Verdict | Snapshot OK | Final Verdict |
|---------------|-------------|---------------|
| PASS | yes | PASS |
| WARN | yes | WARN |
| FAIL | yes | FAIL |
| BLOCKED | yes | BLOCKED |
| *any* | no | FAIL |
| BLOCKED | no | BLOCKED |

## API

```python
from core.governance_failure_regression_packet import (
    build_governance_failure_regression_packet,
    packet_to_dict,
    packet_to_markdown,
)

pkt = build_governance_failure_regression_packet(
    failures,
    title="Regression",
    expected_markdown=previous_markdown,  # optional snapshot
    notes=["note"],
)
d = packet_to_dict(pkt)
md = packet_to_markdown(pkt)
```

## All Layers Pure

- No network
- No file I/O
- No live system dependency
- Deterministic output
