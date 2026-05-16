# Account Risk Guard (Testnet)

## 概览
`account_risk_guard` 是提交前的账户级风控闸门。它不替代 symbol 级 preflight，而是在 preflight 通过后再判断账户是否还能承受新增仓位。

`CLEAN` 与 `BLOCKED` 是两个不同维度：
- `CLEAN`：当前仓位结构安全（例如 `FLAT_CLEAN` / `FULLY_PROTECTED`）。
- `BLOCKED`：根据账户限额规则，当前不允许新增提交（即使状态是 CLEAN）。

## 默认配置（config.yaml）

```yaml
account_risk:
  enabled: true
  max_open_positions: 1
  max_total_notional_usdt: 100
  max_symbol_notional_usdt: 60
  max_daily_submits: 3
  max_pending_or_approved_candidates: 3
  allow_add_to_existing_position: false
  block_if_any_orphan: true
  block_if_any_partial: true
  block_if_any_naked: true
  block_if_duplicate_candidate_ids: true
```

如果 `config.yaml` 缺失该段或缺失子字段，系统会自动回退到安全默认值。

## 字段说明
- `enabled`：总开关。`false` 时仅输出检查结果，不拦截。
- `max_open_positions`：最大允许持仓 symbol 数（`FULLY_PROTECTED` 也算持仓）。
- `max_total_notional_usdt`：账户总名义价值上限（当前 + 本次目标）。
- `max_symbol_notional_usdt`：单 symbol 名义价值上限。
- `max_daily_submits`：UTC 当日最大真实提交次数。
- `max_pending_or_approved_candidates`：待处理候选上限。
- `allow_add_to_existing_position`：是否允许对已有持仓 symbol 继续加仓。
- `block_if_any_orphan` / `block_if_any_partial` / `block_if_any_naked`：发现对应风险态时是否直接阻断。
- `block_if_duplicate_candidate_ids`：候选 ID 冲突是否阻断。

## 为什么默认 `max_open_positions=1`
当前 testnet 轮班目标是单仓位、单链路、可审计。限制为 1 可以降低并发风险、减少恢复复杂度，并让每轮验收更可解释。

## 为什么默认 `max_total_notional_usdt=100`
该值用于控制 testnet 试单规模，确保在“可观测 + 可回滚”的低风险区间内验证执行链路，而不是追求收益。

## 只读检查命令

```bash
PYTHONPATH=. ./.venv/bin/python scripts/check_account_risk_guard.py \
  --env testnet \
  --symbols FETUSDT,OPUSDT \
  --target-symbol OPUSDT \
  --target-notional-usdt 50 \
  --json
```

## 临时放宽 testnet 限额（仅人工）
建议只调整必要字段，且先保留 `block_if_any_*` 为 `true`。例如临时把 `max_open_positions` 从 1 调到 2，用于验证多仓位行为。完成验证后应恢复更严格值。

## 不建议绕过 `ignore-account-risk`
`ignore-account-risk` 只应在明确演练场景下由人工临时使用。常规轮班中绕过会破坏“先阻断、后人工确认”的安全闭环。

## live 前的最小要求
进入 live 前至少连续 30 天保持更严格配置（建议不低于当前默认严格度），并持续观测：
- 非预期 CRITICAL/ERROR 是否为 0；
- 候选/提交/回写/验收链路是否稳定；
- 风险恢复流程是否可重复执行。
