# Governance Failure Examples

Deterministic example builders for tests, docs, CLI demos.

## Builders

| Function | Kind | Verdict | Description |
|----------|------|---------|-------------|
| `build_pass_example_failures()` | pass | PASS | Empty failure list |
| `build_warn_example_failures()` | warn | WARN | Warning-level, retryable only |
| `build_fail_example_failures()` | fail | FAIL | Error-level failure |
| `build_blocked_example_failures()` | blocked | BLOCKED | Critical non-retryable failure |
| `build_mixed_example_failures()` | mixed | BLOCKED | Mixed severities (critical present) |
| `build_example_report(kind)` | any | varies | Serialized report dict |
| `build_example_packet(kind)` | any | varies | Serialized regression packet dict |

## Usage

```python
from core.governance_failure_examples import (
    build_pass_example_failures,
    build_warn_example_failures,
    build_fail_example_failures,
    build_blocked_example_failures,
    build_mixed_example_failures,
    build_example_report,
    build_example_packet,
)

# Get failure lists
pass_failures = build_pass_example_failures()  # []
warn_failures = build_warn_example_failures()  # 2 warnings, retryable
fail_failures = build_fail_example_failures()  # 1 error, non-retryable
blocked_failures = build_blocked_example_failures()  # 1 critical, non-retryable
mixed_failures = build_mixed_example_failures()  # 3 mixed severity

# Build report dict
report = build_example_report("warn")  # {"verdict": "WARN", ...}

# Build regression packet dict
packet = build_example_packet("fail")  # {"final_verdict": "FAIL", ...}
```

## Constraints

- Pure data construction, no I/O
- No timestamps, no random, no environment values
- Stable ordering across calls
- Unsupported kind raises `ValueError`
