# Governance Failure Stack Manifest

Pure data model describing the governance failure reporting stack.
No repo scanning. No file I/O. No network.

## Components

| Task | Name | Module | Test | Doc |
|------|------|--------|------|-----|
| T786 | taxonomy | core/governance_failure_taxonomy.py | tests/unit/test_governance_failure_taxonomy.py | docs/governance_failure_taxonomy.md |
| T787 | report | core/governance_failure_report.py | tests/unit/test_governance_failure_report.py | docs/governance_failure_report.md |
| T788 | snapshot | core/governance_failure_snapshot.py | tests/unit/test_governance_failure_snapshot.py | docs/governance_failure_reporting_stack.md |
| T789 | regression_packet | core/governance_failure_regression_packet.py | tests/unit/test_governance_failure_regression_packet.py | docs/governance_failure_reporting_stack.md |

## Verdict Logic

- PASS: all components COMPLETE
- WARN: any component PARTIAL
- FAIL: any component MISSING

## Usage

```python
from core.governance_failure_stack_manifest import (
    build_expected_governance_stack_manifest,
    manifest_to_dict,
    manifest_to_markdown,
    summarize_manifest,
)

# default: all complete
m = build_expected_governance_stack_manifest()
assert m.verdict == "PASS"

# override statuses
from core.governance_failure_stack_manifest import ComponentStatus
m = build_expected_governance_stack_manifest(
    statuses={"T788": ComponentStatus.PARTIAL}
)
assert m.verdict == "WARN"
```
