# Verification Script Dry-Run Only Proof Policy

**Task ID:** T1283
**release_hold:** HOLD
**Status:** Active

## Policy

Every verification script must provide a dry-run-only proof before approval.

## Proof Requirements

1. **No exchange client instantiation** — `ccxt.*.exchange()` calls must be absent or fully mocked
2. **No order submission paths** — `create_order`, `submit_order`, `place_order` must be absent or patched
3. **No network I/O** — `requests.get/post`, `urlopen`, `aiohttp` must be absent or mocked
4. **No credential access** — `os.environ[API_KEY]` patterns must be absent or guarded

## Proof Methods

### Static Proof
- Grep script for exchange-adjacent function names
- Confirm all matches are inside mock contexts or comments

### Runtime Proof
- Run script with `EXCHANGE_API_KEY=""` and confirm no crash
- Run script with network disabled and confirm pass
- Capture stdout/stderr and confirm no auth errors

## Acceptance

- Script passes static and runtime proof = PASS
- Script fails either proof = HOLD until remediation
- Ambiguous cases escalated to human reviewer
