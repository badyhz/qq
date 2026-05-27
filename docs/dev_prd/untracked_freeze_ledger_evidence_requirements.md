# T1166 - Untracked Freeze Ledger: Evidence Requirements

## Overview

Every state transition for an untracked file must be backed by an evidence record.
The evidence record captures who did what, why, and with what level of safety
verification.

## Required Evidence Fields

| Field                  | Type    | Required For                          |
|------------------------|---------|---------------------------------------|
| classification_record  | bool    | All transitions                       |
| risk_assessment        | bool    | Transitions to FROZEN or QUARANTINED |
| human_approval         | bool    | Transitions out of QUARANTINED       |
| safety_check           | bool    | Transitions involving HIGH risk       |

## Evidence by Transition

### NEW -> STALE
- classification_record: YES (file must have been classified at least once)
- risk_assessment: NO
- human_approval: NO
- safety_check: NO

### NEW -> FROZEN
- classification_record: YES
- risk_assessment: YES (operator must confirm risk class)
- human_approval: YES
- safety_check: YES (if HIGH risk)

### NEW -> DUPLICATE
- classification_record: YES
- risk_assessment: NO (hash match is deterministic)
- human_approval: NO (detection is automated; action on duplicate requires approval)
- safety_check: NO

### NEW -> ORPHAN
- classification_record: YES
- risk_assessment: NO (reference scan is deterministic)
- human_approval: NO (detection is automated; action on orphan requires approval)
- safety_check: NO

### Any -> QUARANTINED
- classification_record: YES
- risk_assessment: YES
- human_approval: YES
- safety_check: YES (if HIGH risk)

### QUARANTINED -> (any)
- classification_record: YES
- risk_assessment: YES
- human_approval: YES (mandatory; terminal state can only be exited by human)
- safety_check: YES

## Evidence Storage

Evidence records are stored in the ledger alongside the file entry. Each record
is immutable once written; corrections require appending a new record that
references the original.
