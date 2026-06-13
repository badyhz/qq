# Testnet Dry-run Adapter Registry

**Total adapters:** 2

## Adapter Details

### scripts/replay_shadow_order_plans_as_testnet_dry.py

- **Adapter type:** dry_run_replay
- **Description:** Replays shadow order plans as testnet dry-run payloads
- **Risk reason:** Public exchange info call, submit path explicitly stubbed out, writes dry-run payloads
- **Network access:** public_exchange_info_only
- **Submit path:** explicitly_stubbed
- **Key usage:** none
- **Dry-run locked:** True
- **No submit:** True
- **Governance tracked:** True

### scripts/verify_testnet_repair_scenarios.py

- **Adapter type:** dry_run_diagnostic
- **Description:** Read-only testnet diagnostic with repair plan generation
- **Risk reason:** Read-only testnet diagnostic, force-locks dry_run=True, produces repair plans
- **Network access:** testnet_read_only
- **Submit path:** force_dry_run_locked
- **Key usage:** read_only_no_secret
- **Dry-run locked:** True
- **No submit:** True
- **Governance tracked:** True
