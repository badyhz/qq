# T792 — Governance Failure Verdict Matrix

**Date:** 2026-05-27
**Status:** PASS

## Overview

Pure decision table mapping `(report_verdict, snapshot_ok)` → `final_verdict`.
No I/O. No network. No runtime dependency.

## Rules

| Report Verdict | Snapshot OK | Final Verdict | Reason |
|----------------|-------------|---------------|--------|
| PASS | yes | PASS | report PASS + snapshot ok |
| WARN | yes | WARN | report WARN + snapshot ok |
| FAIL | yes | FAIL | report FAIL + snapshot ok |
| BLOCKED | yes | BLOCKED | report BLOCKED + snapshot ok |
| PASS | no | FAIL | snapshot mismatch |
| WARN | no | FAIL | snapshot mismatch |
| FAIL | no | FAIL | snapshot mismatch |
| BLOCKED | no | BLOCKED | BLOCKED always wins |
| *unknown* | * | FAIL | unknown verdict fallback |

Priority: BLOCKED > snapshot mismatch > report verdict passthrough

## API

```python
from core.governance_failure_verdict_matrix import (
    resolve_governance_final_verdict,
    build_governance_verdict_matrix,
    verdict_matrix_to_dict,
    verdict_matrix_to_markdown,
)

verdict = resolve_governance_final_verdict("PASS", True)
matrix = build_governance_verdict_matrix()
```
