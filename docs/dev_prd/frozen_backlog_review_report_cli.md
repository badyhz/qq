# Frozen Backlog Review Report CLI (T1561)

## Purpose

CLI interface for generating frozen backlog review reports from the governance layer. Produces read-only reports on frozen file status, review evidence, and governance compliance.

## Usage

```bash
# Generate frozen backlog review report (markdown)
python3 -m scripts.frozen_backlog_review_report --format markdown

# Generate frozen backlog review report (JSON)
python3 -m scripts.frozen_backlog_review_report --format json

# Generate with specific scope
python3 -m scripts.frozen_backlog_review_report --scope high-risk
python3 -m scripts.frozen_backlog_review_report --scope medium-risk
python3 -m scripts.frozen_backlog_review_report --scope all

# Output to file
python3 -m scripts.frozen_backlog_review_report --format markdown --output reports/frozen_backlog_review.md
```

## Commands

| Command | Description |
|---|---|
| `--format markdown` | Output report in markdown format |
| `--format json` | Output report in JSON format |
| `--scope high-risk` | Include only HIGH-risk frozen files |
| `--scope medium-risk` | Include only MEDIUM-risk governed files |
| `--scope all` | Include all governed files (default) |
| `--output PATH` | Write report to file instead of stdout |
| `--dry-run` | Preview report without writing (default) |

## Report Sections

1. **Frozen File Inventory** -- List of all 9 HIGH-risk frozen files with status
2. **Review Evidence** -- Evidence collected per frozen file
3. **Governance Compliance** -- Compliance status against safety boundaries
4. **Human Approval Status** -- Required approvals and their status
5. **Recommendation** -- Hold/unlock recommendation based on evidence

## Safety

- CLI is read-only. No file modifications.
- No exchange connectivity.
- No credential access.
- All outputs are advisory only.
- Release hold: HOLD.
