# No-Submit Release Gate Exchange Client Policy

Task: T1186

## Rules

### No BinanceConnector Instantiation

BinanceConnector must not be instantiated in any code path.

### No BinanceTestnetClient for Live

BinanceTestnetClient must not be repurposed for live order submission.

### No Exchange Factory Calls

No factory function may produce a live exchange client.
