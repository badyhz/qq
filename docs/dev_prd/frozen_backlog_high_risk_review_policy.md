# Frozen Backlog HIGH-Risk Review Policy

**Task:** T1262
**Status:** release_hold = HOLD
**Scope:** 9 HIGH-risk frozen files

## Definition

HIGH-risk files contain live execution paths, order submission logic,
or credential-adjacent functionality. These files require maximum scrutiny.

## Inventory

- core/live_runner.py - runtime execution entry
- core/single_call_recorder.py - call capture with potential side effects
- core/evidence_recorder.py - evidence capture (core + utils dual copy)
- scripts/run_signal_testnet_trial.py - testnet signal trial
- scripts/submit_approved_candidates.py - candidate submission
- scripts/submit_replayed_testnet_payload.py - replayed payload submit
- scripts/run_testnet_order_smoke.py - order smoke test
- scripts/safe_flatten_testnet_symbol.py - position flatten
- scripts/run_spot_testnet_acceptance.py - spot acceptance

## Review Rules

1. Read-only access only - no edits, no execution
2. Every review must produce an evidence artifact
3. No promotion to tracked status without human approval (T1266)
4. Import analysis required - map all dependencies
5. Side-effect audit required - identify network/file mutations

## Prohibited Actions

- Editing any HIGH-risk frozen file
- Committing any HIGH-risk frozen file
- Running any HIGH-risk frozen file
- Importing from HIGH-risk frozen file into tracked code

## Escalation

Any attempt to violate HIGH-risk review rules triggers escalation
to human reviewer with full context of attempted action.
