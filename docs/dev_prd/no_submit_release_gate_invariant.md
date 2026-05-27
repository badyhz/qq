# No-Submit Release Gate Invariants

Task: T1182

## Rules

### No Order Placement

No code path may call any function that submits an order to an exchange.

### No Position Modification

No code path may modify an existing position on any exchange account.

### No Account Mutation

No code path may alter account state (balance, margin, collateral).

### No Exchange API Calls

No code path may make HTTP/WS requests to any exchange endpoint.
