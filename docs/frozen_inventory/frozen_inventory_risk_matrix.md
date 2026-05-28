# Frozen Inventory Risk Matrix

**release_hold = HOLD**
**advisory_only = True**
**human_review_required = True**

## Risk Keyword Frequency

| Keyword | Files Affected | Risk Level |
|---------|---------------|------------|
| testnet | 14 | HIGH - direct exchange interaction |
| order | 12 | HIGH - order lifecycle |
| binance | 10 | HIGH - exchange client |
| submit | 8 | HIGH - order submission |
| live | 3 | CRITICAL - production trading |
| api_key | 4 | CRITICAL - credential exposure |
| secret | 4 | CRITICAL - credential exposure |
| fapi | 3 | HIGH - futures API endpoint |
| flatten | 4 | HIGH - position management |
| cancel | 4 | HIGH - order cancellation |
| requests | 3 | MEDIUM - HTTP client |
| exchange | 3 | HIGH - exchange interaction |
| runtime | 6 | MEDIUM - execution loop |
| shadow | 7 | MEDIUM - shadow trading |
| observation | 8 | LOW - read-only observation |
| approve | 2 | MEDIUM - approval workflow |
| release | 2 | MEDIUM - risk release |
| websocket | 0 | LOW |
| httpx | 0 | LOW |
| aiohttp | 0 | LOW |
| urllib | 0 | LOW |
| positionRisk | 0 | LOW |
| planner | 0 | LOW |

## Risk Level Definitions

- **CRITICAL**: Files that could directly cause real money exposure, credential leaks, or unauthorized trading
- **HIGH**: Files that interact with exchange APIs, manage orders/positions, or submit trades
- **MEDIUM**: Files that support trading infrastructure but do not directly submit orders
- **LOW**: Files with minimal direct trading risk

## Category Risk Summary

| Category | Risk Level | Rationale |
|----------|------------|-----------|
| LIVE | CRITICAL | Direct production trading capability |
| TESTNET | HIGH | Exchange interaction on testnet |
| SUBMIT | HIGH | Order submission path |
| FLATTEN | HIGH | Position management / flattening |
| CANCEL | HIGH | Order cancellation capability |
| SHADOW | MEDIUM | Shadow trading simulation |
| OBSERVATION | LOW-MEDIUM | Read-only observation, some runtime |
| VERIFY | LOW | Verification / validation only |
| RUNTIME | MEDIUM | Runtime loop infrastructure |
| UNKNOWN | VARIABLE | Needs manual classification |
