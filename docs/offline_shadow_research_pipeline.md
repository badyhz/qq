# Offline Shadow Research Pipeline

## Architecture Overview

The offline shadow research pipeline runs trading experiments against historical
data without any live execution, order submission, or exchange connectivity.
It is the primary mechanism for evaluating parameter sets, symbols, and
timeframes before any deployment decision.

```
┌─────────────────────────────────────────────────────────────────┐
│                    OFFLINE SHADOW PIPELINE                      │
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│  │ Fixtures │──>│  Plan    │──>│  Matrix  │──>│  Metric  │    │
│  │  Loader  │   │Generator │   │Material. │   │  Engine  │    │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘    │
│       │                                              │         │
│       v                                              v         │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│  │  Safety  │   │  Eval-   │   │ Score-   │   │  Compar- │    │
│  │  Policy  │──>│  uator   │──>│  card    │──>│  ison    │    │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘    │
│                                                      │         │
│                                                      v         │
│                               ┌──────────┐   ┌──────────┐     │
│                               │  Report  │<──│ Recom-   │     │
│                               │ Renderer │   │ mendation│     │
│                               └──────────┘   └──────────┘     │
│                                     │                           │
│                                     v                           │
│                               ┌──────────┐                     │
│                               │  Bundle  │                     │
│                               │  Builder │                     │
│                               └──────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

## Module Descriptions

### Domain Models (core/)

| Module | Description |
|--------|-------------|
| `offline_shadow_symbol.py` | Frozen dataclass: symbol, base/quote asset, exchange |
| `offline_shadow_timeframe.py` | Frozen dataclass: label, minutes |
| `offline_shadow_window.py` | Frozen dataclass: window_id, type, start/end index |
| `offline_shadow_parameter_set.py` | Frozen dataclass: thresholds, stop/TP, hold limits |
| `offline_shadow_safety_policy.py` | Frozen dataclass: no_live, no_submit, no_exchange, release_hold |
| `offline_shadow_run_config.py` | Frozen dataclass: symbols, timeframes, windows, paths |
| `offline_shadow_experiment.py` | Frozen dataclass: combines all above per experiment |
| `offline_shadow_experiment_plan.py` | Frozen dataclass: plan_id, experiments, run_config, safety_policy |

### Pipeline Modules (core/)

| Module | Description |
|--------|-------------|
| `offline_shadow_fixture_loader.py` | Loads experiment fixtures from YAML/JSON files |
| `offline_shadow_plan_generator.py` | Generates experiment plans from config |
| `offline_shadow_matrix_materializer.py` | Materializes experiment matrix from plan |
| `offline_shadow_metric_engine.py` | Computes run-level and aggregate metrics |
| `offline_shadow_evaluator.py` | Evaluates experiments against quality gates |
| `offline_shadow_scorecard.py` | Produces per-experiment quality grades |
| `offline_shadow_comparison.py` | Compares multiple experiments side-by-side |
| `offline_shadow_report_renderer.py` | Renders reports in text/JSON formats |
| `offline_shadow_bundle_builder.py` | Builds final artifact bundle with manifest |
| `offline_shadow_recommendation_engine.py` | Generates DEPLOY/WATCH/REJECT recommendations |

### CLI Scripts (scripts/)

| Script | Description |
|--------|-------------|
| `run_offline_shadow_research_pipeline.py` | Runs the full pipeline end-to-end |
| `build_offline_shadow_research_bundle.py` | Builds the artifact bundle |

## Data Flow

```
1. Load fixtures from tests/fixtures/offline_shadow_research/
2. Generate experiment plan (symbol x timeframe x window x params)
3. Materialize experiment matrix
4. For each experiment:
   a. Compute run metrics from outcome records
   b. Evaluate against quality gates
   c. Assign scorecard grade (A/B/C/D/REJECT)
5. Compare experiments across dimensions
6. Generate recommendations (DEPLOY/WATCH/REJECT)
7. Render reports (text summary, JSON detail)
8. Build bundle with sha256 manifest
9. Write output to output_dir
```

## CLI Usage

### Run Full Pipeline

```bash
python3 scripts/run_offline_shadow_research_pipeline.py \
    --fixture-dir tests/fixtures/offline_shadow_research \
    --output-dir /tmp/shadow_output
```

### Build Bundle Only

```bash
python3 scripts/build_offline_shadow_research_bundle.py \
    --input-dir /tmp/shadow_output \
    --output-bundle /tmp/shadow_bundle.tar.gz
```

### Run Tests

```bash
python3 -m pytest tests/unit/test_offline_shadow_*.py -v
```

## Safety Invariants

These invariants are enforced at the data model level and must never be
violated:

1. **release_hold == "HOLD"** -- All safety policies must have
   `release_hold="HOLD"`. Any other value raises `ValueError` at
   construction time. This is the master kill switch.

2. **no_live == True** -- No live execution is ever permitted in the
   shadow pipeline.

3. **no_submit == True** -- No order submission is ever permitted.

4. **no_exchange == True** -- No exchange connectivity is ever permitted.

5. **Frozen dataclasses** -- All domain models are `@dataclass(frozen=True)`.
   Once constructed, they cannot be mutated.

6. **No I/O in core/** -- Core modules contain only pure functions and
   frozen dataclasses. No network calls, file I/O, or exchange
   interaction.

7. **Explicit git add** -- Files are never staged with `git add .`.
   Each file must be explicitly added.

## Troubleshooting

### "release_hold must be 'HOLD'" error

The safety policy was constructed with a non-"HOLD" value. This is
intentional -- the pipeline only operates under hold. Check your
fixture files or config.

### Empty metrics

If `compute_run_metrics` returns all zeros, check that:
- Outcome records contain `return_r` keys
- The outcome list is not empty
- Values are numeric (not strings or None)

### Import errors

Ensure you run from the repository root:
```bash
cd /Users/winnie/Documents/trae_projects/qq
python3 -m pytest tests/unit/test_offline_shadow_*.py -v
```

### Fixture loading failures

Fixture files must be valid YAML/JSON. Each fixture must contain all
required fields for the domain models. See `tests/fixtures/` for
examples.
