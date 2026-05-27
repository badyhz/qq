# Historical Backtest Research Bundle — Artifact Specification

## Bundle Contents

The research bundle packages all backtest artifacts for reproducibility:

| Artifact | Format | Description |
|----------|--------|-------------|
| `plan.json` | JSON | Experiment plan: symbols, timeframes, parameters |
| `matrix.json` | JSON | Materialized parameter grid with all presets |
| `results.json` | JSON | Per-run evaluation results |
| `scorecard.json` | JSON | Scorecard grading per run and experiment |
| `report.md` | Markdown | Human-readable report |
| `report.html` | HTML | Dashboard with visual styling |
| `report.json` | JSON | Structured report for programmatic access |
| `manifest.json` | JSON | Bundle manifest with safety flags + SHA256 |

## Manifest Structure

```json
{
  "release_hold": "HOLD",
  "no_live": true,
  "no_submit": true,
  "no_exchange": true,
  "artifact_count": 7,
  "artifacts": [
    {"name": "plan.json", "sha256": "abc123..."},
    {"name": "matrix.json", "sha256": "def456..."},
    ...
  ]
}
```

### Safety Flags

- `release_hold`: Always "HOLD"
- `no_live`: Always true — no live trading
- `no_submit`: Always true — no order submission
- `no_exchange`: Always true — no exchange client usage

### Artifact Descriptors

Each artifact has:
- `name`: filename
- `sha256`: hex-encoded SHA-256 hash of content

## SHA256 Verification

`compute_sha256(content)` accepts `str` or `bytes`:
- Strings are encoded to UTF-8 bytes before hashing
- Returns 64-character hex digest
- Deterministic: same content always produces same hash

Verification flow:
1. Build bundle via `build_bundle()`
2. Extract `manifest.json` from bundle
3. For each artifact, recompute SHA-256
4. Compare with manifest values
5. All must match for bundle integrity

## Bundle Assembly

`build_bundle()` is a pure function:
- Takes all artifact contents as parameters
- Returns dict mapping filename to content string
- Includes `manifest.json` with computed hashes
- No file I/O — caller handles persistence

## Usage Pattern

```python
from core.offline_shadow_bundle_builder import build_bundle, compute_sha256

bundle = build_bundle(
    plan_data=plan,
    matrix_data=matrix,
    results_data=results,
    scorecard_data=scorecard,
    report_markdown=md_str,
    report_html=html_str,
    report_json=json_dict,
)

# Write to disk (caller responsibility)
for filename, content in bundle.items():
    write_to_output_dir(filename, content)
```

## Integrity Guarantees

1. SHA-256 is computed on the exact content stored in the bundle
2. Manifest includes all artifacts — no partial bundles
3. Safety flags are hardcoded — cannot be overridden
4. All functions are pure — no side effects
