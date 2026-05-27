# T817 — Runtime Governance Frozen Boundary Map

**Date:** 2026-05-27
**Status:** PASS

## Overview

Document frozen boundaries as data.

## Boundaries

| ID | Pattern | Reason | Status |
|----|---------|--------|--------|
| live_trading | scripts/*live* | no live trading | frozen |
| submit_scripts | scripts/submit* | no submit | frozen |
| secrets | *.env, *credentials* | no secret access | frozen |
| planner | core/planner* | planner integration frozen | frozen |
| runtime_execution | core/live_runner.py | runtime execution frozen | frozen |
| exchange_client | core/exchange* | exchange client mutation frozen | frozen |

## API

```python
from core.runtime_governance_frozen_boundary_map import (
    build_runtime_governance_frozen_boundary_map,
    frozen_boundary_map_to_dict,
    frozen_boundary_map_to_markdown,
)
```
