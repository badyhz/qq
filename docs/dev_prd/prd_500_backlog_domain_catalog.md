# PRD 500-Backlog Domain Catalog

## Purpose

Partition 500+ backlog tasks into 10 deterministic domains. Each domain carries risk level, file scope, and review requirements. No live execution is authorized by any domain.

## Domains

| ID | Title | Risk | Tasks | Human Review |
|----|-------|------|-------|--------------|
| D01 | PRD Control Plane | LOW | 80 | no |
| D02 | Backlog Planning | MEDIUM | 80 | no |
| D03 | Readonly Hook Design | LOW | 60 | no |
| D04 | Offline Evidence Design | LOW | 50 | no |
| D05 | Manual Review CLI Design | MEDIUM | 50 | no |
| D06 | Readonly Hook Review | HIGH | 50 | yes |
| D07 | Runtime Integration Review | HIGH | 50 | yes |
| D08 | Live Execution (Frozen) | FROZEN | 40 | yes |
| D09 | Regression and Closeout | LOW | 50 | no |
| D10 | Route and Agent Operations | MEDIUM | 40 | no |

**Total domains:** 10
**Total target tasks:** 500

## Frozen Domain Note

D08 (Live Execution) is FROZEN. No task may authorize live execution, real order placement, or autonomous planning. All domains block access to secrets, credentials, api_keys, and .env files.

## Live Authorization

No domain in this catalog authorizes live trading. This is intentional — live execution requires explicit out-of-band approval outside the domain catalog system.
