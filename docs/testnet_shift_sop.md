# Testnet Shift SOP

## 1) 班前检查
- 仅使用 `env=testnet`。
- `export PYTHONPATH=.`
- 如需代理，先设置 `HTTP_PROXY/HTTPS_PROXY`。
- 注入 `BINANCE_TESTNET_API_KEY` 与 `BINANCE_TESTNET_API_SECRET`，禁止打印 secret。
- 先执行状态检查：

```bash
PYTHONPATH=. ./.venv/bin/python scripts/check_testnet_state.py --env testnet --symbol FETUSDT --json
PYTHONPATH=. ./.venv/bin/python scripts/check_testnet_state.py --env testnet --symbol OPUSDT --json
```

## 2) 观察班次

```bash
PYTHONPATH=. ./.venv/bin/python scripts/run_scheduled_observation.py \
  --env testnet \
  --symbols FETUSDT,OPUSDT \
  --dry-run \
  --json
```

## 3) 候选生成

```bash
PYTHONPATH=. ./.venv/bin/python scripts/build_execution_candidates.py \
  --env testnet \
  --input-jsonl logs/replayed_testnet_dry_payloads_exchangeinfo.jsonl \
  --output-jsonl logs/execution_candidates.jsonl \
  --symbols FETUSDT,OPUSDT \
  --allowlist FETUSDT,OPUSDT \
  --dry-run
```

查看候选：

```bash
PYTHONPATH=. ./.venv/bin/python scripts/manage_execution_candidates.py \
  --candidates-jsonl logs/execution_candidates.jsonl \
  --action list \
  --json
```

规则：真实提交前只允许 `approve` 一个 symbol 的一个候选。

## 4) 审批规则
- 审批前必须先执行账户级风控只读检查：

```bash
PYTHONPATH=. ./.venv/bin/python scripts/check_account_risk_guard.py \
  --env testnet \
  --symbols FETUSDT,OPUSDT \
  --target-symbol <SYMBOL> \
  --target-notional-usdt <NOTIONAL> \
  --json
```

- 若 `allowed=false`，禁止真实 submit。
- `preflight_status=FLAT_CLEAN`
- `risk_flags=[]`（或仅可接受的低风险标记）
- `notional_usdt` 不超过小额测试上限
- `symbol` 在 allowlist
- 不同时批准多个候选用于真实提交

## 5) 执行桥 dry-run

```bash
PYTHONPATH=. ./.venv/bin/python scripts/submit_approved_candidates.py \
  --env testnet \
  --candidates-jsonl logs/execution_candidates.jsonl \
  --allowlist FETUSDT,OPUSDT \
  --dry-run \
  --json
```

## 6) 真实 testnet submit（人工执行）
- 执行前人工二次核对：
  - `check_account_risk_guard.py` 输出 `allowed=true`
  - `candidate-id`
  - `symbol`
  - `amount`
  - `FLAT_CLEAN`
  - `allowlist`
  - `--allow-testnet-submit`
  - `--dry-run false`

命令模板（仅人工）：

```bash
PYTHONPATH=. ./.venv/bin/python scripts/submit_approved_candidates.py \
  --env testnet \
  --candidate-id <CANDIDATE_ID> \
  --allowlist FETUSDT,OPUSDT \
  --dry-run false \
  --allow-testnet-submit \
  --max-approved-candidates 1 \
  --submit-protective-orders true \
  --json
```

## 7) 提交后验收

```bash
PYTHONPATH=. ./.venv/bin/python scripts/check_testnet_state.py --env testnet --symbol <SYMBOL> --json
PYTHONPATH=. ./.venv/bin/python scripts/manage_execution_candidates.py --action show --candidate-id <CANDIDATE_ID> --json
PYTHONPATH=. ./.venv/bin/python scripts/generate_testnet_acceptance_report.py --run-dir logs/approved_candidate_runs/<RUN_ID>
PYTHONPATH=. ./.venv/bin/python scripts/generate_daily_observation_summary.py --date <YYYY-MM-DD> --json
```

## 8) 异常处理
- `ORPHAN_PROTECTION`：先 `safe_flatten` dry-run，再人工 `--confirm`。
- `PARTIAL_PROTECTED`：执行 `verify_testnet_repair_scenarios.py` 并修复。
- `NAKED_POSITION`：立即停止新单，优先补保护单或平仓。
- `API_AUTH_FAILED` / `missing key`：停止执行，修正 key 与权限。
- `ORDER_WOULD_IMMEDIATELY_TRIGGER`：重算保护价。
- `LIVE_SUBMIT_BLOCKED`：确认是否预期安全阻断事件。

## 9) 清理流程

```bash
PYTHONPATH=. ./.venv/bin/python scripts/safe_flatten_testnet_symbol.py --env testnet --symbol <SYMBOL> --dry-run --cancel-protective-orders --close-position --json
PYTHONPATH=. ./.venv/bin/python scripts/safe_flatten_testnet_symbol.py --env testnet --symbol <SYMBOL> --cancel-protective-orders --close-position --confirm --json
PYTHONPATH=. ./.venv/bin/python scripts/check_testnet_state.py --env testnet --symbol <SYMBOL> --json
```

## 10) 禁止事项
- 禁止 live。
- 禁止未经 approval 直接 submit。
- 禁止批量真实提交多个 symbol。
- 禁止打印 secret。
- 禁止跳过 check state。
- 禁止在 `account_risk_guard.allowed=false` 时强行真实 submit。

## 11) 轮班记录模板
- 日期：
- 操作人：
- symbols：
- candidates：
- approved candidate：
- submit result：
- final state：
- report path：
- risk events：
- next actions：

## 12) 定时任务限制
- cron/launchd 仅允许执行 dry-run observation。
- 禁止在定时任务中执行真实 submit。

## 13) Clean Shift 验收流程
1. 先归档只读状态快照（见第 14 节）。
2. 生成 clean-window 日报（见第 15 节）。
3. 生成 shift review report（见第 16 节）。
4. 仅当 clean-window verdict 与 shift review verdict 都为 `PASS` 才可判定本次班次通过。

## 14) 生成状态快照（只读）
```bash
PYTHONPATH=. ./.venv/bin/python scripts/archive_testnet_state_snapshot.py \
  --env testnet \
  --symbols FETUSDT,OPUSDT \
  --json
```

## 15) 生成 clean-window 日报
```bash
PYTHONPATH=. ./.venv/bin/python scripts/generate_daily_observation_summary.py \
  --date 2026-05-06 \
  --risk-events-jsonl logs/risk_events_scoped_v4.jsonl \
  --production-only \
  --clean-window true \
  --since-utc 2026-05-06T00:00:00+00:00 \
  --json
```

## 16) 生成 shift review report
```bash
PYTHONPATH=. ./.venv/bin/python scripts/generate_shift_review_report.py \
  --date 2026-05-06 \
  --risk-events-jsonl logs/risk_events_scoped_v4.jsonl \
  --candidates-jsonl logs/execution_candidates.jsonl \
  --approved-runs-dir logs/approved_candidate_runs \
  --json
```

## 17) PASS / PARTIAL / FAIL 判定原则
- 允许 PASS：
  - clean-window 内无 non-expected critical/error/warning；
  - 状态快照 `aggregate_status=CLEAN`；
  - artifact 校验 `ok=true`；
  - 无 submit_failed。
- 只能 PARTIAL：
  - clean-window 内仅 warning；
  - 或存在 pending/approved 候选待处理；
  - 或仅 optional artifacts 缺失。
- 必须停止（FAIL）：
  - 出现 `NAKED_POSITION`；
  - 出现真实 submit/protective failure；
  - 出现 non-expected critical/error；
  - 状态快照 `aggregate_status=CRITICAL`。

## 18) 第三轮/后续轮次准入
- 若已有 `FULLY_PROTECTED` 持仓且 `max_open_positions=1`，账户级风控应返回 `allowed=false`，此时禁止继续真实 submit。
- 若需要继续下一轮，必须二选一：
  1. 先按流程释放已有仓位（先 dry-run，再人工 confirm，再复查）；  
  2. 人工调整 testnet `account_risk` 配置并记录变更理由。
