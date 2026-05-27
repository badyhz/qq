# Runtime Governance Dry-Run Adapter

Evaluates the runtime governance contract in dry-run mode using the existing governance failure reporting stack.

## Overview

- Pure: no I/O, no network, no random, no timestamps
- Deterministic output
- Composes: contract validation -> failure report -> regression packet -> verdict matrix

## API

### `evaluate_runtime_governance_dry_run(inp, *, expected_markdown=None, notes=None)`

Returns `RuntimeGovernanceDryRunResult` with:
- `contract_result` — validation output
- `report` — failure report (PASS if no failures)
- `packet` — regression packet with optional snapshot check
- `final_verdict` — from verdict matrix: PASS / WARN / FAIL / BLOCKED

### `dry_run_result_to_dict(result) -> Dict`

Serialization. Keys: input, contract_result, report, packet, final_verdict, mode, notes.

### `dry_run_result_to_markdown(result) -> str`

Deterministic markdown. No timestamps.

## Verdict Logic

1. Validate input via `validate_runtime_governance_input`
2. Build report from failures
3. Build regression packet with optional `expected_markdown` snapshot
4. `resolve_governance_final_verdict(report.verdict, packet.snapshot_diff.ok)`
5. If contract ok + no failures + snapshot ok: verdict = "PASS"
