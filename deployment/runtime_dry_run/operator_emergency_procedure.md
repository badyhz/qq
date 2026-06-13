# Operator Emergency Procedure

## Immediate Actions

### 1. Stop Scheduled Dry-Run
Disable all scheduled E2E runs immediately.

### 2. Freeze New Submit Intents
Block creation of new submit intent packets.

### 3. Enable Kill Switch
Set kill switch to ENABLED_BLOCKING state.

### 4. Archive Current Runtime Artifacts
Copy all runtime artifacts to timestamped archive directory.

### 5. Export Audit Log
Export full audit log for review and forensic analysis.

### 6. Review Pending Approvals
Deny all pending approval requests immediately.

### 7. Confirm No Real Orders
Verify no real orders were submitted during the incident.

## Escalation

### 8. Manual Escalation Checklist
- Notify operator team
- Document incident timeline
- Preserve evidence

### 9. Rollback Procedure
Restore to last known good state from archive.

### 10. Post-Incident Review
Document incident, root cause, and lessons learned.

## Implementation

All emergency procedures are implemented in:
`src/runtime_integrations/testnet_presubmit/operator_emergency_procedure.py`
