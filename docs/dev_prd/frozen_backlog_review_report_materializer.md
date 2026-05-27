# Frozen Backlog Review Report Materializer (T1562)

## Purpose

Materializes frozen backlog review report artifacts from governance models into renderable formats (markdown, JSON). Bridges the gap between frozen dataclass models and CLI output.

## Materialization Pipeline

```
Governance Models -> Materializer -> Renderer -> CLI Output
```

## Input Models

| Model | Source | Description |
|---|---|---|
| `FrozenBacklogReviewPacket` | governance model | Per-file review evidence |
| `GovernanceSummaryPacket` | governance model | Aggregate governance status |
| `SafetyBoundaryPacket` | governance model | Safety boundary compliance |
| `HumanApprovalEvidencePacket` | governance model | Human approval records |

## Output Formats

### Markdown

- Section-per-file inventory
- Table-formatted compliance matrix
- Human-readable recommendation block

### JSON

- Structured report object
- Machine-parseable for downstream tooling
- Schema: `{ "report_version", "generated_at", "scope", "files", "compliance", "recommendation" }`

## Materializer Functions

| Function | Input | Output |
|---|---|---|
| `materialize_frozen_inventory(scope)` | scope filter | list of frozen file records |
| `materialize_review_evidence(files)` | file list | evidence records per file |
| `materialize_compliance_matrix(evidence)` | evidence records | compliance status matrix |
| `materialize_recommendation(compliance)` | compliance matrix | hold/unlock recommendation |
| `render_report(data, format)` | materialized data | formatted output |

## Safety

- All materializer functions are pure (no side effects).
- No file system writes (CLI handles output).
- No exchange connectivity.
- No credential access.
- All outputs are advisory only.
- Release hold: HOLD.
