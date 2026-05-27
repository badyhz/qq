# Governance Failure CLI Renderer

Deterministic CLI renderer for governance failure regression packets.

## Usage

```bash
# Pass sample — markdown
python scripts/render_governance_failure_regression_packet.py --sample pass

# Warn sample — json
python scripts/render_governance_failure_regression_packet.py --sample warn --format json

# Fail sample — strict mode (exits 1)
python scripts/render_governance_failure_regression_packet.py --sample fail --strict

# Blocked sample — json, strict mode
python scripts/render_governance_failure_regression_packet.py --sample blocked --format json --strict
```

## Options

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `--sample` | `pass`, `warn`, `fail`, `blocked` | (required) | Sample scenario |
| `--format` | `markdown`, `json` | `markdown` | Output format |
| `--strict` | flag | off | Exit 1 for FAIL/BLOCKED |

## Exit Codes

| Condition | Exit Code |
|-----------|-----------|
| PASS/WARN sample | 0 |
| FAIL/BLOCKED sample (no --strict) | 0 |
| FAIL/BLOCKED sample (with --strict) | 1 |
| Invalid --sample | 2 (argparse error) |
| Invalid --format | 2 (argparse error) |

## Sample Scenarios

- **pass** — No failures. Verdict: PASS.
- **warn** — Single retryable rate-limit warning. Verdict: WARN.
- **fail** — Error-severity adapter failure + warning. Verdict: FAIL.
- **blocked** — Critical non-retryable policy block + error. Verdict: BLOCKED.

## Properties

- Deterministic: no timestamps, no environment-dependent values.
- Stable key ordering for JSON (`sort_keys=True`).
- Stable markdown ordering (sorted categories, severities).
- No file I/O. Stdout only.
- No network. No live system dependency.
