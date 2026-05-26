# Execution Guard Report Examples

## Glossary

| Term | Meaning |
|---|---|
| **fail-closed** | Unknown or missing state defaults to blocked; never silently proceeds |
| **layered unlock** | 5-layer gate (capability → CLI allow → env unlock → manual confirm → symbol allowlist) required before action |
| **kill-switch** | `QQ_NO_*` env var that unconditionally blocks an action regardless of other layers |
| **schema drift** | Producer output diverging from schema-required keys; caught by contract tests |
| **guard report** | Structured dict emitted per action, validated against schema before output |
| **HIGH_RISK_WRITE** | Scripts that submit/cancel/flatten orders (frozen until Phase3) |
| **HIGH_RISK_RUNTIME** | Long-running orchestrators that may trigger actions (frozen until Phase4) |

## 1. dry_run OK

```json
{
  "status": "OK",
  "mode": "dry_run",
  "action": "submit",
  "env_overrides": {
    "QQ_NO_SUBMIT": false,
    "QQ_NO_CANCEL": false,
    "QQ_NO_FLATTEN": false,
    "QQ_NO_LIVE": false,
    "QQ_REQUIRE_DRY_RUN": false
  },
  "symbol": "BTCUSDT",
  "symbol_allowlist": ["BTCUSDT", "ETHUSDT"],
  "layer0_blocked": false,
  "layer1_capability": true,
  "layer2_cli_allow": true,
  "layer3_env_unlock": true,
  "layer4_manual_confirm": true,
  "layer5_symbol_ok": true
}
```

## 2. live BLOCKED

```json
{
  "status": "BLOCKED",
  "reason": "LIVE_MODE_NOT_ALLOWED",
  "mode": "live",
  "action": "submit",
  "symbol": "BTCUSDT",
  "env_overrides": {
    "QQ_NO_SUBMIT": false,
    "QQ_NO_CANCEL": false,
    "QQ_NO_FLATTEN": false,
    "QQ_NO_LIVE": false,
    "QQ_REQUIRE_DRY_RUN": false
  }
}
```

## 3. QQ_NO_SUBMIT blocked

```json
{
  "status": "OK",
  "mode": "dry_run",
  "action": "submit",
  "env_overrides": {
    "QQ_NO_SUBMIT": true,
    "QQ_NO_CANCEL": false,
    "QQ_NO_FLATTEN": false,
    "QQ_NO_LIVE": false,
    "QQ_REQUIRE_DRY_RUN": false
  },
  "symbol": "BTCUSDT",
  "symbol_allowlist": [],
  "layer0_blocked": true,
  "layer1_capability": true,
  "layer2_cli_allow": true,
  "layer3_env_unlock": true,
  "layer4_manual_confirm": true,
  "layer5_symbol_ok": true
}
```

## 4. missing mode blocked

```json
{
  "status": "BLOCKED",
  "reason": "FAIL_CLOSED",
  "mode": "",
  "action": "submit",
  "symbol": "BTCUSDT",
  "env_overrides": {
    "QQ_NO_SUBMIT": false,
    "QQ_NO_CANCEL": false,
    "QQ_NO_FLATTEN": false,
    "QQ_NO_LIVE": false,
    "QQ_REQUIRE_DRY_RUN": false
  }
}
```

## 5. symbol allowlist reject

```json
{
  "status": "OK",
  "mode": "dry_run",
  "action": "submit",
  "env_overrides": {
    "QQ_NO_SUBMIT": false,
    "QQ_NO_CANCEL": false,
    "QQ_NO_FLATTEN": false,
    "QQ_NO_LIVE": false,
    "QQ_REQUIRE_DRY_RUN": false
  },
  "symbol": "DOGEUSDT",
  "symbol_allowlist": ["BTCUSDT", "ETHUSDT"],
  "layer0_blocked": false,
  "layer1_capability": true,
  "layer2_cli_allow": true,
  "layer3_env_unlock": true,
  "layer4_manual_confirm": true,
  "layer5_symbol_ok": false
}
```

## 6. full layered unlock pass

```json
{
  "status": "OK",
  "mode": "testnet",
  "action": "submit",
  "env_overrides": {
    "QQ_NO_SUBMIT": false,
    "QQ_NO_CANCEL": false,
    "QQ_NO_FLATTEN": false,
    "QQ_NO_LIVE": false,
    "QQ_REQUIRE_DRY_RUN": false
  },
  "symbol": "BTCUSDT",
  "symbol_allowlist": ["BTCUSDT"],
  "layer0_blocked": false,
  "layer1_capability": true,
  "layer2_cli_allow": true,
  "layer3_env_unlock": true,
  "layer4_manual_confirm": true,
  "layer5_symbol_ok": true
}
```
