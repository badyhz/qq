# PRD 500 Backlog JSON Pack — T913

Deterministic serialization of all 500-backlog analysis maps into a single JSON-serializable pack.

## What it does

`build_prd_500_json_pack(backlog)` assembles:

- Full backlog dict (via `backlog_to_dict`)
- Milestone map (via `build_prd_500_milestone_map`)
- Wave map (via `build_prd_500_wave_map`)
- Batch map (via `build_prd_500_batch_map`)
- Dependency map (via `build_prd_500_dependency_map`)
- Risk map (via `build_prd_500_risk_map`)
- Final verdict (worst of dependency + risk verdicts)
- Merged notes

## Outputs

| Function              | Returns         |
|-----------------------|-----------------|
| `build_prd_500_json_pack` | `Prd500JsonPack` |
| `json_pack_to_dict`   | `dict`          |
| `json_pack_to_string` | `str` (sorted JSON) |

## Properties

- Pure deterministic — no I/O, no timestamps, no random
- `json_pack_to_string` uses `sort_keys=True` for reproducibility
- Final verdict: PASS / WARN / BLOCKED / FAIL (worst of dependency + risk)

## Tests

```
python3 -m pytest tests/unit/test_prd_500_backlog_json_pack.py -q
```
