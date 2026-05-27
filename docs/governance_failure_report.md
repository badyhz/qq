# T787 — Governance Failure Report

**Date:** 2026-05-27
**Status:** PASS

## Overview

Pure reporting layer on top of governance failure taxonomy.
Converts `GovernanceFailure` objects into deterministic dict/markdown reports.
No network. No file I/O. No live system dependency.

## Verdict Rules

| Condition | Verdict |
|-----------|---------|
| No failures | PASS |
| Failures exist, no ERROR, no CRITICAL | WARN |
| Any ERROR or CRITICAL | FAIL |
| Any CRITICAL non-retryable | BLOCKED |

Priority: BLOCKED > FAIL > WARN > PASS

## API

```python
from core.governance_failure_report import (
    build_governance_failure_report,
    report_to_dict,
    report_to_markdown,
)

report = build_governance_failure_report(failures, title="My Report", notes=["note"])
d = report_to_dict(report)
md = report_to_markdown(report)
```

## Markdown Sections (stable order)

1. Title + verdict summary
2. By Category (sorted alphabetically)
3. By Severity (sorted alphabetically)
4. Top Sources (sorted by count desc, then name asc)
5. Failures (in input order)
6. Notes
