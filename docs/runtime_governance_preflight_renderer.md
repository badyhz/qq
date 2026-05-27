# Runtime Governance Preflight Renderer

## Overview

Pure renderer for `RuntimeGovernancePreflightPacket`. No I/O. No timestamps. Deterministic.

## API

### `render_preflight_summary(packet) -> Dict[str, Any]`

Compact summary dict with keys: `final_verdict`, `proceed`, `ready`, `blocker_count`, `failure_count`, `contract_ok`, `notes_count`.

- `ready` = `True` when `proceed` is `True` and no blockers exist.

### `render_preflight_markdown(packet) -> str`

Full markdown rendering with 7 sections. Deterministic output — repeated calls with identical input always produce identical output.

### `render_preflight_compact_dict(packet) -> Dict[str, Any]`

Minimal dict for logging: `verdict`, `proceed`, `failures` (count).

## Markdown Sections

1. `# Runtime Governance Preflight` — title
2. `## Final Verdict` — verdict + proceed
3. `## Ready For Runtime` — boolean ready flag
4. `## Blockers` — CRITICAL or non-retryable failures, sorted by category
5. `## Failures` — all contract failures with retryable indicator, sorted by category
6. `## Audit Event` — rendered via `audit_event_to_markdown`
7. `## Notes` — bullet list

## Determinism

- No timestamps injected anywhere.
- Failures sorted by `category.value`.
- All output is a pure function of the input packet.
