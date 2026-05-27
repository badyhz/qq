# T786 — Governance Failure Taxonomy

**Date:** 2026-05-27
**Status:** PASS

## Overview

Structured classification layer for governance/workflow/runtime safety failures.
Pure simulation — no network, no I/O, no live system dependency.

## Categories

| Category | Default Severity | Retryable | Trigger |
|----------|-----------------|-----------|---------|
| POLICY_BLOCK | CRITICAL | No | Forbidden action, governance violation |
| SANDBOX_BLOCK | ERROR | No | Domain/method blocked by sandbox |
| ADAPTER_FAILURE | ERROR | No | Adapter returned error |
| TRANSPORT_FAILURE | WARNING | No | Connection/transport layer error |
| VALIDATION_FAILURE | ERROR | No | Schema/field validation failure |
| TIMEOUT | WARNING | Yes | 408/504 status or timeout keyword |
| RATE_LIMIT | WARNING | Yes | 429 status or rate_limit keyword |
| UNKNOWN | ERROR | No | Fallback for unclassifiable failures |

## Severity Levels

| Level | Meaning |
|-------|---------|
| INFO | Informational, no action needed |
| WARNING | Transient, may resolve on retry |
| ERROR | Failure, needs attention |
| CRITICAL | Hard block, immediate halt |

## Classification Logic

Priority order:
1. Explicit `category` parameter (always wins)
2. HTTP status code mapping
3. Message keyword matching
4. UNKNOWN fallback

Severity resolution:
1. Explicit `severity` parameter
2. HTTP status code mapping
3. Category default

Retryable resolution:
1. Explicit `retryable` parameter
2. Category membership (RATE_LIMIT, TIMEOUT → True)
3. Status code membership (429, 408, 502, 503, 504 → True)
4. False

## API

```python
from core.governance_failure_taxonomy import (
    classify_governance_failure,
    failure_to_dict,
    summarize_failures,
)

# Classify
f = classify_governance_failure(status_code=429, message="rate limited")

# Serialize
d = failure_to_dict(f)

# Aggregate
summary = summarize_failures([f1, f2, f3])
```
