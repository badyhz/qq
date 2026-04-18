# Safety Rules

## Current Phase: Skeleton Stage

This file defines safety principles. Some sections are applicable now, others will apply when features are implemented.

## Immediately Applicable Rules

### Credential Management
- **NEVER** hardcode API keys in code
- **NEVER** commit secrets to git
- **ALWAYS** read from environment variables
- Use .env files for local development (never committed)

### Error Handling
- Never let exceptions crash the system silently
- All critical errors must be logged
- All errors must have user-friendly messages
- Implement error count thresholds (stop on repeated errors)

### Configuration Safety
- Validate all configuration on startup
- Provide sensible defaults
- Reject invalid configurations
- Document all config parameters

### Logging Safety
- Never log sensitive data (API keys, tokens)
- Log all trades for audit (when implemented)
- Log all order changes (when implemented)
- Log all system state changes

### Code Safety - Numerical Calculations
- Use Decimal for all financial calculations
- Round to appropriate precision
- Never compare floats for equality
- Implement currency-specific precision

### Graceful Shutdown
- Handle SIGTERM/SIGINT gracefully
- Complete pending operations
- Save state before exit (when state management implemented)
- Log shutdown reason

## Future Rules (To Apply When Features Implemented)

### API Safety (Apply when R11 - Binance API implemented)
- Respect Binance API rate limits
- Implement request queuing
- Use WebSocket for real-time data when possible
- Implement exponential backoff on failures
- Implement connection timeout
- Handle network failures gracefully

### Financial Safety (Apply when trading logic implemented)
- All features must work in dry-run mode
- Dry-run mode must be the default
- Live mode requires explicit configuration
- No code path skips dry-run guard
- Validate order size before placement
- Validate order price reasonableness
- Prevent negative or zero orders

### Risk Limits (Apply when risk management implemented)
- Hard stop limits: defined in config
- Auto-shutdown on critical risk breach
- Emergency manual stop mechanism
- Minimum balance check before any trade
- Reserve minimum for operations

### State Consistency (Apply when R13 implemented)
- State must be recoverable from crashes
- Critical state must be persisted
- Implement state checksums
- Validate state on startup

### Data Safety (Apply when data feeds implemented)
- Validate timestamp of incoming data
- Reject stale data
- Validate price ranges (detect bad data)
- Implement data quality checks

### Concurrency Safety (Apply when order management implemented)
- Lock all shared state
- Implement thread-safe order management
- Prevent race conditions on balance
- Use async/await where appropriate

### Operational Safety (Apply when monitoring implemented)
- Implement health check endpoint
- Check system resources (memory, CPU)
- Check exchange connectivity
- Alert on unhealthy state

## Incident Response Principles

### On Critical Failure
1. Stop all operations immediately
2. Log full system state
3. Notify administrator (when notification implemented)
4. Wait for manual intervention
5. Validate before restart

### On Data Anomaly (when implemented)
1. Log anomaly details
2. Pause new operations
3. Investigate data source
4. Resume after validation

## Reference

See PROJECT_STATE.md for current phase
See feature_list.json for implementation status
