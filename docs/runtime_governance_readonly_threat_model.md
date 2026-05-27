# Runtime Governance Read-Only Threat Model (T847)

## Purpose

Threat model for the read-only governance design. Pure, deterministic module — no I/O, no timestamps, no random.

## Threats

| threat_id | severity | title | vector | mitigation | status |
|---|---|---|---|---|---|
| readonly_bypass | critical | Read-only bypass via permission escalation | permission envelope manipulation | invariant checker + permission envelope validation | open |
| permission_creep | high | Permission creep beyond read-only | gradual permission expansion | strict boundary enforcement + rollback plan | open |
| secret_leak | critical | Secret or credential leak in read-only layer | observability data exposure | redaction rules + encrypted storage for sensitive signals | open |
| planner_override | critical | Planner override of read-only constraints | planner autonomous mode | planner integration frozen + manual approval gate | open |
| network_exfiltration | high | Network exfiltration via read-only hook | covert network channel | network invariant checker + no network declaration | open |

## API

- `build_readonly_threat_model()` — returns canonical list of 5 `RuntimeGovernanceReadOnlyThreat` dataclasses
- `readonly_threat_model_to_dict(threats)` — list of dicts
- `readonly_threat_model_to_markdown(threats)` — markdown table string
- `summarize_readonly_threat_model(threats)` — summary with total, by_severity, by_status
