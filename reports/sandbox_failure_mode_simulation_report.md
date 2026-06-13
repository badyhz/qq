# Sandbox Failure Mode Simulation Report

## Rate Limit

Exceeded: False
Action: OK: within limits
No real sleep: True

## Network Failure

All handled: True
No real network: True

## Scenarios

- timeout: handled=True, action=retry with backoff, max 3 retries
- connection_error: handled=True, action=fail fast, report to operator
- partial_response: handled=True, action=reject partial, request full snapshot
- malformed_response: handled=True, action=reject, log raw response
- duplicate_response: handled=True, action=dedup by order_id, ignore duplicate
- out_of_order: handled=True, action=reject stale sequence, request fresh
- stale_response: handled=True, action=reject if older than 5s, request fresh

## Conclusion

RATE_LIMIT_SIMULATION_PASS
NETWORK_FAILURE_SIMULATION_PASS
