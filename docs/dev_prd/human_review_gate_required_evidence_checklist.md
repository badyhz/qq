# Human Review Gate Required Evidence Checklist

## Per Gate Type

### TRADING Gate

- [ ] Test results: all unit tests pass
- [ ] Test results: integration tests pass (dry-run)
- [ ] Safety verification: no live order path active
- [ ] Safety verification: dry-run mode enforced
- [ ] Documentation: action description complete
- [ ] Documentation: affected symbols/assets listed
- [ ] Human sign-off: L2+ operator approval
- [ ] Frozen file integrity: execution.py, order_manager.py verified

### CREDENTIAL Gate

- [ ] Test results: config loader tests pass
- [ ] Safety verification: no hardcoded secrets
- [ ] Safety verification: env vars only for credentials
- [ ] Documentation: which credentials accessed
- [ ] Documentation: purpose of access
- [ ] Human sign-off: L3+ admin approval
- [ ] Frozen file integrity: config_loader.py, config.yaml verified

### CONNECTION Gate

- [ ] Test results: connection mock tests pass
- [ ] Safety verification: no real API calls in test
- [ ] Safety verification: testnet endpoint used
- [ ] Documentation: target exchange and endpoint
- [ ] Documentation: connection purpose
- [ ] Human sign-off: L2+ operator approval
- [ ] Frozen file integrity: data_feed.py, execution.py verified

### PLANNER Gate

- [ ] Test results: planner logic tests pass
- [ ] Safety verification: planner does not auto-execute
- [ ] Safety verification: human approval required before execution
- [ ] Documentation: planner input/output specification
- [ ] Human sign-off: L3+ admin approval
- [ ] Frozen file integrity: signal_engine.py, main.py verified

### FROZEN_FILE Gate

- [ ] Test results: affected module tests pass
- [ ] Safety verification: freeze tag integrity pre-check
- [ ] Safety verification: no contamination of unrelated frozen files
- [ ] Documentation: reason for frozen file modification
- [ ] Documentation: diff of proposed changes
- [ ] Human sign-off: L3+ admin approval
- [ ] Frozen file integrity: all HIGH-risk files re-verified post-change

### RISK_PARAMETER Gate

- [ ] Test results: risk manager tests pass
- [ ] Safety verification: new limits within acceptable bounds
- [ ] Safety verification: no risk bypass possible
- [ ] Documentation: parameter change details
- [ ] Documentation: impact analysis
- [ ] Human sign-off: L3+ admin approval
- [ ] Frozen file integrity: risk_manager.py, config.yaml, config_loader.py verified
