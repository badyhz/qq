# Multi-Strategy Research Workbench / Parameter Search / Portfolio-Level Lab PRD

目标文件：`docs/dev_prd/multi_strategy_research_workbench_prd.md`

项目范围：`T4201-T5200 Multi-Strategy Research Workbench / Parameter Search / Portfolio-Level Lab`

依据：用户提供的 PRD 要求与安全边界。

---

## 1. Executive Summary

当前量化系统已经从早期单点脚本、shadow observation、testnet dry-run 安全验证，逐步演进为具备治理、安全冻结、离线研究、历史 OHLCV 回测能力的工程化研究系统。

截至 T4200，系统已完成 Historical OHLCV Offline Backtest Engine，具备真实本地 OHLCV CSV fixture、chunked reader、walk-forward、breakout signal、offline trade simulator、scorecard、comparison、bundle、manifest 等能力，并且测试规模已经稳定到 6041 tests passing。

但是当前系统仍主要围绕单策略 Historical OHLCV Backtest Lab 展开。它可以验证单一 breakout 类策略，但不足以支撑下一阶段研究需求：

* 多策略统一接入；
* 多参数搜索；
* 多 symbol / timeframe matrix；
* 样本内、样本外、walk-forward 对比；
* 策略间相关性与重叠度分析；
* 组合级收益、回撤、暴露聚合；
* 策略晋级、观察、淘汰机制；
* 研究 artifact 可索引、可回归、可审计。

因此，T4201-T5200 的目标是将系统升级为 **Multi-Strategy Research Workbench / Parameter Search / Portfolio-Level Lab**。

该 Workbench 必须保持完全本地、离线、只读、安全、确定性、可测试、可回归。它不是交易系统，不连接任何交易所，不做 testnet submit，不做 live trading，不接 runtime，不接 planner，只生成本地研究 artifact、报告、bundle 和 manifest。

---

## 2. Current System State

当前系统已完成以下关键阶段：

* `T961-T1060 read-only hook governance`
* `T1061-T1160 freeze-aware governance`
* `T1161-T1260 untracked freeze governance`
* `T1261-T1360 frozen backlog review governance`
* `T1361-T1440 governance operating layer`
* `T1441-T1520 review-to-decision operating system`
* `T1521-T1600 frozen backlog report CLI / packet materializer`
* `T1601-T1800 validator / snapshot / diff / audit automation`
* `T1801-T2200 frozen backlog review platform v1`
* `T2201-T2600 unit test stabilization`

  * unit tests 曾达到 `5218 passed / 6 skipped / 0 failed`
* `T2601-T3200 Offline Shadow Research Pipeline`

  * 已完成 plan / matrix / results / report / scorecard / manifest 端到端 pipeline
* `T3201-T4200 Historical OHLCV Offline Backtest Engine`

  * 已完成真实本地 OHLCV CSV fixture
  * 已完成 chunked reader
  * 已完成 walk-forward
  * 已完成 breakout signal
  * 已完成 trade simulator
  * 已完成 scorecard
  * 已完成 comparison
  * 已完成 bundle
  * 当前测试状态达到 `6041 tests passing`

当前系统具备：

* 成熟 governance layer；
* frozen backlog review platform；
* 稳定 unit test 基线；
* 离线 shadow research pipeline；
* historical OHLCV backtest lab；
* 本地 artifact / manifest 输出能力；
* 安全冻结与 release hold 意识。

当前缺口：

* 缺少多策略统一接口；
* 缺少 strategy registry；
* 缺少多策略 adapter；
* 缺少参数搜索引擎；
* 缺少多策略 / 多 symbol / 多 timeframe matrix；
* 缺少组合级 aggregation；
* 缺少策略相关性 / overlap 分析；
* 缺少 out-of-sample robustness scoring；
* 缺少策略 promotion / rejection policy；
* 缺少统一 workbench report；
* 缺少完整 bundle builder；
* 缺少面向下一阶段研究入库的 artifact index。

---

## 3. Product Goal

构建一个完全离线、本地、确定性、可测试、可回归的多策略研究工作台。

该 Workbench 的目标是：

1. 允许多个策略通过统一接口注册和执行；
2. 支持 breakout / mean reversion / momentum continuation / volatility compression breakout 等基础策略族；
3. 支持 bounded grid search 和 search budget guard；
4. 支持多 symbol / 多 timeframe / 多 split / 多 parameter set 的 experiment matrix；
5. 支持 walk-forward 与 out-of-sample evaluation；
6. 支持组合级收益、回撤、暴露、交易重叠分析；
7. 支持策略间 correlation / overlap / concentration 风险识别；
8. 支持 robustness / sensitivity / degradation 分析；
9. 支持策略晋级、观察、淘汰、人工审核建议；
10. 支持 research artifact index；
11. 支持 markdown / json / html report；
12. 支持 bundle builder；
13. 支持 manifest with sha256；
14. 支持 end-to-end CLI；
15. 支持 golden fixtures、negative tests、安全边界测试和 full acceptance checklist。

核心原则：

```text
local_only = true
offline_only = true
read_only = true
deterministic = true
testable = true
regression_safe = true
release_hold = HOLD
```

---

## 4. Non-goals

本 PRD 明确不做以下事项：

* 不做实盘交易；
* 不做 testnet submit；
* 不连接 Binance；
* 不连接任何交易所；
* 不自动下单；
* 不撤单；
* 不 flatten；
* 不 submit；
* 不读取 API key；
* 不读取 secrets；
* 不接 runtime；
* 不接 planner；
* 不做实时行情；
* 不下载数据；
* 不联网；
* 不处理生产级大数据湖；
* 不建立数据库服务；
* 不做 Web 后台；
* 不做自动参数过拟合上线；
* 不把研究结果自动接入交易执行；
* 不解冻 frozen backlog；
* 不修改 frozen backlog 文件；
* 不执行 frozen backlog 文件；
* 不 import exchange / live / submit / runtime / planner 模块；
* 不改变 release hold；
* 不新增任何 live unlock 机制；
* 不把 `PROMOTE_TO_NEXT_RESEARCH_ROUND` 解释为上线许可。

---

## 5. Safety Boundary

本项目必须严格遵守以下安全规则。

### 5.1 Global Safety Flags

所有 manifest、report、artifact index、bundle 均必须包含或继承以下安全状态：

```json
{
  "release_hold": "HOLD",
  "no_live": true,
  "no_submit": true,
  "no_exchange": true,
  "no_runtime_integration": true,
  "no_planner_integration": true,
  "no_network": true,
  "local_artifact_only": true,
  "fixture_only": true
}
```

### 5.2 Hard Prohibitions

执行期间禁止：

* 任何网络请求；
* 任何交易所 client 初始化；
* 任何 Binance 连接；
* 任何 testnet submit；
* 任何 live trading；
* 任何 order placement；
* 任何 cancel；
* 任何 flatten；
* 任何 submit；
* 任何 real exchange client；
* 任何 runtime integration；
* 任何 planner integration；
* 任何 secrets / credentials / API keys 读取；
* 任何 frozen backlog 文件修改；
* 任何 frozen backlog 文件执行；
* 任何 frozen backlog 文件 import；
* `git add .`；
* 隐式 staging；
* 批量误提交。

### 5.3 Required Git Discipline

必须使用 explicit git add。

允许形式：

```bash
git add docs/dev_prd/multi_strategy_research_workbench_prd.md
git add core/research_workbench_*.py
git add tests/unit/test_*.py
```

禁止形式：

```bash
git add .
git add -A
git commit -am
```

### 5.4 Output Boundary

所有输出只能是：

* local fixture；
* local JSON artifact；
* local Markdown report；
* local HTML report；
* local manifest；
* local bundle；
* local test output。

默认目标输出目录：

```text
/tmp/multi_strategy_research_workbench
```

### 5.5 Release Hold

`release_hold` 必须始终保持：

```text
HOLD
```

任何阶段不得将其改为：

```text
READY
APPROVED
LIVE
SUBMIT
UNLOCKED
```

---

## 6. Forbidden Files

以下 22 个 frozen backlog 文件在 PRD 执行期间必须保持完全冻结。

规则：

* 不得修改；
* 不得 import；
* 不得执行；
* 不得 git add；
* 不得 commit；
* 不得重命名；
* 不得格式化；
* 不得删除；
* 不得作为实现依赖；
* 只能作为本文档中列出的安全边界存在。

### 6.1 HIGH-risk Frozen Files

```text
core/live_runner.py
scripts/live_playbook.py
scripts/submit_approved_candidates.py
scripts/run_testnet_order_smoke.py
scripts/run_signal_testnet_trial.py
scripts/run_spot_testnet_acceptance.py
scripts/safe_flatten_testnet_symbol.py
scripts/replay_shadow_order_plans_as_testnet_dry.py
scripts/submit_replayed_testnet_payload.py
```

### 6.2 MEDIUM-risk Frozen Files

```text
scripts/run_controlled_testnet_shift.py
scripts/run_daily_shadow_scan_pipeline.py
scripts/run_next_shadow_experiment_plan.py
scripts/run_observation_shift_runtime.py
scripts/run_remediation_shadow_only_loop.py
scripts/run_replay_submit_batch.py
scripts/run_right_breakout_param_observation.py
scripts/run_right_breakout_scan_dry.py
scripts/run_shadow_observation_experiments.py
scripts/run_shadow_sample_collection_pipeline.py
scripts/run_shadow_universe_collector.py
scripts/verify_risk_release_flow.py
scripts/verify_testnet_repair_scenarios.py
```

### 6.3 Frozen File Stop Rule

If any forbidden file becomes modified, staged, executed, imported, or committed, implementation must stop immediately and be marked:

```text
FAIL_SAFETY_BOUNDARY
```

---

## 7. Allowed Areas

本项目只允许在以下区域新增或修改文件。

### 7.1 Allowed Core Areas

```text
core/research_workbench_*.py
core/strategy_research_*.py
core/strategy_registry_*.py
core/parameter_search_*.py
core/portfolio_research_*.py
core/multi_strategy_*.py
core/research_artifact_*.py
```

### 7.2 Allowed Scripts

```text
scripts/run_multi_strategy_research_workbench.py
scripts/generate_strategy_experiment_registry.py
scripts/run_parameter_search_lab.py
scripts/compare_strategy_research_results.py
scripts/build_multi_strategy_research_bundle.py
```

### 7.3 Allowed Docs

```text
docs/dev_prd/*
```

### 7.4 Allowed Tests

```text
tests/unit/*
```

### 7.5 Allowed Fixtures

```text
tests/fixtures/multi_strategy_research/*
```

### 7.6 Reuse Policy

允许复用 existing historical OHLCV backtest lab 中的安全、离线、只读函数，但必须满足：

* 不 import frozen files；
* 不 import live/testnet/submit/runtime/planner modules；
* 不引入网络依赖；
* 不读取 secrets；
* 不改变 release hold；
* 不改变现有 historical backtest behavior；
* 仅通过纯函数或 local fixture 进行研究计算。

---

## 8. User Stories

1. 作为研究者，我希望用统一接口注册多个策略，以便不同策略可以被同一套 matrix、evaluation、report 工具处理。

2. 作为研究者，我希望 breakout、mean reversion、momentum continuation、volatility compression breakout 都能通过统一 adapter 输出相同格式的 signal。

3. 作为研究者，我希望对多个策略运行相同 walk-forward split，以便公平比较样本内、验证集、测试集表现。

4. 作为研究者，我希望在 BTCUSDT、ETHUSDT 等多个 symbol 上同时评估策略，以便识别策略是否只对单一品种有效。

5. 作为研究者，我希望在 5m、15m 等多个 timeframe 上运行相同策略，以便观察 timeframe sensitivity。

6. 作为研究者，我希望做 bounded grid search，并且有 search budget guard，以避免参数组合爆炸和过拟合。

7. 作为研究者，我希望看到每个参数组合的 train / validation / test score，以便判断策略是否存在样本外退化。

8. 作为负责人，我希望看到策略晋级 / 观察 / 淘汰建议，以便决定下一轮研究优先级。

9. 作为负责人，我希望 manifest 证明 no_live / no_submit / no_exchange / no_runtime / no_planner / no_network，以便确保研究工作没有越过安全边界。

10. 作为负责人，我希望看到策略之间的 signal overlap 和 trade overlap，以便避免多个策略实际上押注同一类行情。

11. 作为负责人，我希望看到 portfolio-level aggregation，以便理解多个策略组合后的收益、回撤、暴露、集中度。

12. 作为负责人，我希望 report.md、report.json、report.html 同时生成，以便给人类审阅、机器回归和后续归档。

13. 作为 agent，我希望有明确 stop conditions，以便在 frozen files、release_hold、network、exchange、runtime/planner 边界触发时立即停止。

14. 作为 agent，我希望有 deterministic artifact output，以便 golden regression tests 可以稳定比较。

15. 作为研究者，我希望 artifact index 记录 artifact id、path、sha256、related strategy、release_hold、安全 flags，以便后续追踪研究证据链。

16. 作为负责人，我希望所有结果都只保存在本地 `/tmp/multi_strategy_research_workbench`，不上传、不联网、不进入交易执行层。

---

## 9. Functional Requirements

### 9.1 Strategy Interface

系统必须提供统一策略接口，用于定义、验证和执行本地离线策略 adapter。

每个 strategy definition 必须包含：

```text
strategy_id
strategy_family
display_name
description
parameter_schema
required_bar_fields
signal_generation_contract
output_signal_format
safety_notes
deterministic
local_only
no_network
no_exchange
```

#### 9.1.1 Required Fields

`strategy_id`

* string；
* deterministic；
* snake_case；
* example:

  * `breakout`
  * `mean_reversion`
  * `momentum_continuation`
  * `volatility_compression_breakout`

`strategy_family`

* string；
* one of:

  * `breakout`
  * `mean_reversion`
  * `momentum`
  * `volatility_compression`

`parameter_schema`

* bounded schema；
* every numeric parameter must have min / max / default；
* every enum parameter must have allowed values；
* no unbounded parameter search allowed。

`required_bar_fields`

Minimum:

```text
timestamp
open
high
low
close
volume
```

Optional:

```text
symbol
timeframe
source
```

`signal_generation_contract`

Must define:

* input bars；
* parameter set；
* output signals；
* deterministic ordering；
* no mutation of input bars；
* no network；
* no exchange；
* no secrets。

`output_signal_format`

Each signal must include:

```text
signal_id
strategy_id
symbol
timeframe
timestamp
side
entry_reference_price
confidence
metadata
```

`side` allowed:

```text
LONG
SHORT
FLAT
```

Initial implementation may support LONG-only strategies if explicitly declared in `safety_notes`.

`safety_notes`

Must include:

```text
local pure function
offline only
no exchange client
no live trading
no order intent
research signal only
```

### 9.2 Strategy Registry

系统必须支持 strategy registry。

Required capabilities:

* register strategy；
* list strategies；
* validate strategy adapter；
* reject unsafe strategy；
* deterministic registry output；
* JSON export；
* CLI generation；
* safety validation。

Registry must reject strategy if:

* missing `strategy_id`；
* missing `parameter_schema`；
* parameter range unbounded；
* imports forbidden module；
* declares network requirement；
* declares exchange requirement；
* produces non-deterministic output；
* attempts to emit order payload；
* references frozen files；
* references runtime/planner integration。

Registry output must be deterministic:

* stable strategy ordering by `strategy_id`；
* stable JSON keys；
* no timestamp unless explicitly passed；
* deterministic sha256 in bundle manifest。

### 9.3 Strategy Adapters

At least four adapters must be supported.

#### 9.3.1 Breakout Adapter

Strategy id:

```text
breakout
```

Purpose:

* reuse existing safe historical OHLCV breakout logic where possible；
* detect price breakout above local lookback range；
* produce research-only signal。

Example parameters:

```text
lookback_bars
breakout_buffer_pct
min_body_pct
cooldown_bars
stop_loss_pct
take_profit_rr
```

Safety:

* local pure function；
* no live module；
* no exchange；
* no order payload；
* no runtime/planner。

#### 9.3.2 Mean Reversion Adapter

Strategy id:

```text
mean_reversion
```

Purpose:

* detect stretched move away from mean；
* research if short-term reversal has statistical edge。

Example parameters:

```text
lookback_bars
zscore_entry
zscore_exit
min_volume_ratio
cooldown_bars
stop_loss_pct
take_profit_rr
```

Signal logic:

* compute rolling mean；
* compute rolling std；
* generate signal when close deviates beyond threshold；
* output research signal only。

Safety:

* no short execution assumption unless simulator supports it；
* adapter must declare LONG-only or LONG/SHORT support explicitly；
* no order payload。

#### 9.3.3 Momentum Continuation Adapter

Strategy id:

```text
momentum_continuation
```

Purpose:

* identify directional continuation after sustained momentum；
* test whether trend persistence exists after breakout or slope confirmation。

Example parameters:

```text
momentum_lookback_bars
min_return_pct
ema_fast
ema_slow
min_slope_pct
cooldown_bars
stop_loss_pct
take_profit_rr
```

Signal logic:

* compute recent return；
* compute moving average alignment；
* require slope confirmation；
* emit continuation signal。

Safety:

* local only；
* deterministic；
* no exchange dependency。

#### 9.3.4 Volatility Compression Breakout Adapter

Strategy id:

```text
volatility_compression_breakout
```

Purpose:

* identify low volatility compression followed by expansion breakout；
* research squeeze / volatility expansion behavior。

Example parameters:

```text
compression_lookback_bars
max_range_pct
breakout_lookback_bars
breakout_buffer_pct
volume_expansion_ratio
cooldown_bars
stop_loss_pct
take_profit_rr
```

Signal logic:

* detect compressed high-low range；
* confirm breakout above compression range；
* optionally require volume expansion；
* emit research-only signal。

Safety:

* local pure function；
* no live exchange；
* no submit behavior。

### 9.4 Parameter Search Engine

系统必须提供 parameter search engine。

Required capabilities:

* named presets；
* grid search；
* bounded parameter ranges；
* max combination guard；
* deterministic ordering；
* search budget；
* overfit warning；
* skipped combination reporting；
* JSON artifact output。

#### 9.4.1 Named Presets

Each strategy may define presets:

```text
conservative
balanced
aggressive
```

Presets are not production recommendations. They are research seeds only.

#### 9.4.2 Grid Search

Grid search must:

* expand finite parameter values only；
* sort parameters by name；
* sort parameter values deterministically；
* assign stable `parameter_set_id`；
* enforce search budget；
* produce deterministic result order。

#### 9.4.3 Bounded Parameter Ranges

Every searchable parameter must define:

```text
name
type
min
max
default
values
```

No infinite range allowed.

#### 9.4.4 Max Combination Guard

If expanded combinations exceed `--search-budget`, the engine must either:

* truncate deterministically and mark `budget_truncated = true`；or
* fail safely if configured strict。

Default behavior:

```text
budget_truncated = true
overfit_warning = true
```

#### 9.4.5 Search Budget

CLI must expose:

```text
--search-budget
```

Search budget must apply across the requested strategy universe.

#### 9.4.6 Overfit Warning

Parameter search output must include:

```text
overfit_warning
search_budget
expanded_combinations
evaluated_combinations
budget_truncated
small_fixture_warning
```

### 9.5 Multi-Strategy Experiment Matrix

系统必须 build matrix rows across:

```text
strategy
symbol
timeframe
walk_forward_split
parameter_set
fixture_dataset
```

Each row must include:

```text
matrix_row_id
strategy_id
strategy_family
symbol
timeframe
split_id
parameter_set_id
fixture_path
dataset_id
run_mode
release_hold
safety_flags
```

Matrix requirements:

* deterministic row ordering；
* stable ids；
* no timestamp unless explicitly passed；
* no network；
* no exchange；
* no runtime/planner；
* chunked fixture reading；
* large file guard。

### 9.6 Matrix Evaluator

For each matrix row, evaluator must run:

1. data quality check；
2. strategy signal generation；
3. offline trade simulation；
4. metrics；
5. scorecard；
6. safety flag propagation；
7. artifact recording。

Required result fields:

```text
matrix_row_id
strategy_id
symbol
timeframe
split_id
parameter_set_id
data_quality
signal_count
trade_count
win_rate
expectancy_r
avg_return
max_drawdown
profit_factor
avg_mfe
avg_mae
score
warnings
release_hold
safety_flags
```

Data quality check must include:

```text
row_count
missing_required_fields
duplicate_timestamps
non_monotonic_timestamps
null_ohlcv_count
min_timestamp
max_timestamp
coverage_status
```

### 9.7 Portfolio-Level Aggregation

系统必须 support portfolio aggregation across:

* symbols；
* timeframes；
* strategies；
* parameter sets；
* walk-forward splits。

Required outputs:

```text
portfolio_id
included_strategy_ids
included_symbols
included_timeframes
total_trades
aggregate_expectancy_r
aggregate_win_rate
aggregate_profit_factor
max_drawdown_approx
equity_curve_approx
exposure_summary
drawdown_summary
trade_overlap_summary
warnings
```

Portfolio aggregation must support:

* aggregate across symbols；
* aggregate across timeframes；
* aggregate across strategies；
* equity curve approximation；
* drawdown aggregation；
* exposure aggregation；
* trade overlap summary。

Important limitation:

Portfolio aggregation is a research approximation, not a live portfolio engine.

Report must state:

```text
Portfolio aggregation is offline research only and does not imply executable portfolio allocation.
```

### 9.8 Correlation / Overlap Analysis

系统必须 support:

* signal overlap；
* trade overlap；
* same-symbol concentration；
* strategy family concentration；
* timeframe concentration；
* timestamp overlap；
* exposure overlap；
* correlation proxy。

Required fields:

```text
overlap_id
strategy_pair
symbol
timeframe
signal_overlap_count
signal_overlap_ratio
trade_overlap_count
trade_overlap_ratio
same_symbol_concentration
strategy_family_concentration
timeframe_concentration
warnings
```

Overlap warnings:

```text
HIGH_SIGNAL_OVERLAP
HIGH_TRADE_OVERLAP
SAME_SYMBOL_CONCENTRATION
SAME_FAMILY_CONCENTRATION
TIMEFRAME_CONCENTRATION
LOW_SAMPLE_SIZE
```

### 9.9 Out-of-Sample Scoring

系统必须 support train / validation / test scoring.

Required fields:

```text
train_score
validation_score
test_score
stability_penalty
overfit_flag
degradation_flag
sample_size_warning
promotion_score
```

Out-of-sample degradation rules:

* if validation score materially worse than train score, set `degradation_flag = true`；
* if test score materially worse than validation score, set `degradation_flag = true`；
* if train score high and validation/test weak, set `overfit_flag = true`；
* if sample size too small, set `sample_size_warning = true`；
* promotion policy must penalize overfit/degradation。

### 9.10 Strategy Promotion Policy

Promotion recommendation must assign one of:

```text
PROMOTE_TO_NEXT_RESEARCH_ROUND
WATCH_MORE_DATA
REJECT_OVERFIT
REJECT_DRAWDOWN
HUMAN_REVIEW_REQUIRED
KEEP_HOLD
```

Rules:

`PROMOTE_TO_NEXT_RESEARCH_ROUND`

* only means safe research continuation；
* does not mean testnet；
* does not mean live；
* does not unlock submit；
* requires release_hold still HOLD。

`WATCH_MORE_DATA`

* insufficient sample；
* unstable but not failed；
* needs larger local fixture or additional offline research。

`REJECT_OVERFIT`

* train good；
* validation/test poor；
* degradation flag true；
* excessive parameter sensitivity。

`REJECT_DRAWDOWN`

* unacceptable max drawdown；
* portfolio aggregation reveals concentrated loss；
* downside risk dominates expectancy。

`HUMAN_REVIEW_REQUIRED`

* conflicting metrics；
* suspicious result；
* manifest mismatch；
* safety warning；
* next-stage decision required。

`KEEP_HOLD`

* default global state；
* must appear in final manifest；
* must remain true for all outputs。

### 9.11 Research Artifact Index

Artifact index must support:

```text
artifact_id
artifact_type
path
sha256
size_bytes
related_strategy
related_experiment
related_matrix_row
created_by
release_hold
safety_flags
```

Artifact types:

```text
strategy_registry
parameter_search
matrix
results
portfolio_summary
comparison
promotion_recommendations
artifact_index
report_md
report_html
manifest
```

All paths must be local.

No remote URI allowed.

### 9.12 Report Renderers

System must output:

```text
report.md
report.json
report.html
```

Report content must include:

* executive summary；
* strategy registry summary；
* parameter search summary；
* matrix summary；
* result summary；
* portfolio aggregation；
* overlap analysis；
* out-of-sample scoring；
* promotion recommendations；
* warnings；
* safety manifest summary；
* artifact index summary；
* stop condition status。

HTML report:

* static file；
* no external JS；
* no external CSS；
* no remote fonts；
* no network assets；
* all inline CSS if needed；
* deterministic output；
* no timestamp unless passed。

### 9.13 Bundle Builder

CLI:

```text
scripts/build_multi_strategy_research_bundle.py
```

Artifacts:

```text
strategy_registry.json
parameter_search.json
matrix.json
results.json
portfolio_summary.json
comparison.json
promotion_recommendations.json
artifact_index.json
report.md
report.html
manifest.json
```

Bundle builder must:

* verify all required artifacts exist；
* compute sha256；
* compute artifact sizes；
* write manifest；
* validate safety flags；
* fail if release_hold != HOLD；
* fail if forbidden artifact path found；
* fail if remote URI found；
* fail if network/exchange flags false。

### 9.14 Full Pipeline CLI

CLI:

```text
scripts/run_multi_strategy_research_workbench.py
```

Inputs:

```text
--fixture-dir
--output-dir
--strategies
--symbols
--timeframes
--split-mode
--search-budget
--chunk-size
```

Required behavior:

* parse strategy list；
* build registry；
* run parameter search；
* build matrix；
* evaluate matrix；
* aggregate portfolio；
* compare strategies；
* generate promotion recommendations；
* build artifact index；
* render reports；
* build manifest；
* validate bundle；
* exit non-zero on safety violation。

---

## 10. Data Model

### 10.1 StrategyDefinition

```json
{
  "strategy_id": "breakout",
  "strategy_family": "breakout",
  "display_name": "Breakout Strategy",
  "description": "Offline research-only breakout signal adapter.",
  "parameter_schema": {},
  "required_bar_fields": ["timestamp", "open", "high", "low", "close", "volume"],
  "signal_generation_contract": {
    "input": "ordered OHLCV bars",
    "output": "research signals",
    "deterministic": true
  },
  "output_signal_format": "StrategySignal",
  "safety_notes": [
    "local pure function",
    "offline only",
    "no exchange client",
    "no live trading",
    "research signal only"
  ],
  "safety_flags": {
    "no_live": true,
    "no_submit": true,
    "no_exchange": true,
    "no_network": true
  }
}
```

### 10.2 StrategyRegistry

```json
{
  "registry_id": "multi_strategy_research_registry",
  "strategies": [],
  "strategy_count": 0,
  "validation_status": "PASS",
  "rejected_strategies": [],
  "release_hold": "HOLD",
  "safety_flags": {}
}
```

### 10.3 StrategyParameterSchema

```json
{
  "strategy_id": "breakout",
  "parameters": [
    {
      "name": "lookback_bars",
      "type": "int",
      "min": 5,
      "max": 100,
      "default": 20,
      "values": [10, 20, 40]
    }
  ],
  "bounded": true,
  "deterministic_order": true
}
```

### 10.4 StrategyParameterSet

```json
{
  "parameter_set_id": "breakout_ps_0001",
  "strategy_id": "breakout",
  "preset_name": "balanced",
  "parameters": {
    "lookback_bars": 20
  },
  "source": "grid_search",
  "release_hold": "HOLD"
}
```

### 10.5 ParameterSearchSpace

```json
{
  "search_space_id": "search_space_001",
  "strategy_id": "breakout",
  "parameters": [],
  "expanded_combinations": 0,
  "search_budget": 120,
  "bounded": true
}
```

### 10.6 ParameterSearchResult

```json
{
  "search_result_id": "parameter_search_001",
  "strategy_ids": [],
  "search_budget": 120,
  "expanded_combinations": 0,
  "evaluated_combinations": 0,
  "budget_truncated": false,
  "overfit_warning": false,
  "parameter_sets": [],
  "release_hold": "HOLD"
}
```

### 10.7 MultiStrategyMatrixRow

```json
{
  "matrix_row_id": "row_000001",
  "strategy_id": "breakout",
  "strategy_family": "breakout",
  "symbol": "BTCUSDT",
  "timeframe": "5m",
  "split_id": "rolling_001",
  "parameter_set_id": "breakout_ps_0001",
  "fixture_path": "tests/fixtures/historical_backtest_lab/BTCUSDT_5m.csv",
  "dataset_id": "BTCUSDT_5m_fixture",
  "run_mode": "offline_research",
  "release_hold": "HOLD",
  "safety_flags": {}
}
```

### 10.8 StrategySignal

```json
{
  "signal_id": "signal_000001",
  "strategy_id": "breakout",
  "symbol": "BTCUSDT",
  "timeframe": "5m",
  "timestamp": "2024-01-01T00:00:00Z",
  "side": "LONG",
  "entry_reference_price": 100.0,
  "confidence": 0.5,
  "metadata": {}
}
```

### 10.9 StrategyRunResult

```json
{
  "run_result_id": "result_000001",
  "matrix_row_id": "row_000001",
  "strategy_id": "breakout",
  "symbol": "BTCUSDT",
  "timeframe": "5m",
  "split_id": "rolling_001",
  "parameter_set_id": "breakout_ps_0001",
  "data_quality": {},
  "signal_count": 0,
  "trade_count": 0,
  "win_rate": 0.0,
  "expectancy_r": 0.0,
  "avg_return": 0.0,
  "max_drawdown": 0.0,
  "profit_factor": 0.0,
  "avg_mfe": 0.0,
  "avg_mae": 0.0,
  "score": 0.0,
  "warnings": [],
  "release_hold": "HOLD"
}
```

### 10.10 PortfolioAggregateResult

```json
{
  "portfolio_id": "portfolio_research_001",
  "included_strategy_ids": [],
  "included_symbols": [],
  "included_timeframes": [],
  "total_trades": 0,
  "aggregate_expectancy_r": 0.0,
  "aggregate_win_rate": 0.0,
  "aggregate_profit_factor": 0.0,
  "max_drawdown_approx": 0.0,
  "equity_curve_approx": [],
  "exposure_summary": {},
  "drawdown_summary": {},
  "trade_overlap_summary": {},
  "warnings": []
}
```

### 10.11 StrategyComparisonResult

```json
{
  "comparison_id": "comparison_001",
  "strategy_rankings": [],
  "family_summary": {},
  "timeframe_summary": {},
  "symbol_summary": {},
  "overlap_analysis": {},
  "out_of_sample_summary": {},
  "warnings": []
}
```

### 10.12 PromotionRecommendation

```json
{
  "recommendation_id": "promo_000001",
  "strategy_id": "breakout",
  "parameter_set_id": "breakout_ps_0001",
  "symbol": "BTCUSDT",
  "timeframe": "5m",
  "status": "WATCH_MORE_DATA",
  "reasons": [],
  "blocking_risks": [],
  "release_hold": "HOLD",
  "human_review_required": false
}
```

### 10.13 ResearchArtifactIndex

```json
{
  "artifact_index_id": "artifact_index_001",
  "artifacts": [
    {
      "artifact_id": "artifact_000001",
      "artifact_type": "strategy_registry",
      "path": "/tmp/multi_strategy_research_workbench/strategy_registry.json",
      "sha256": "",
      "size_bytes": 0,
      "related_strategy": null,
      "related_experiment": null,
      "created_by": "multi_strategy_research_workbench",
      "release_hold": "HOLD",
      "safety_flags": {}
    }
  ]
}
```

### 10.14 WorkbenchManifest

```json
{
  "manifest_id": "multi_strategy_research_workbench_manifest",
  "generated_by": "scripts/run_multi_strategy_research_workbench.py",
  "release_hold": "HOLD",
  "no_live": true,
  "no_submit": true,
  "no_exchange": true,
  "no_runtime_integration": true,
  "no_planner_integration": true,
  "no_network": true,
  "artifacts": [],
  "sha256": {},
  "artifact_sizes": {},
  "warnings": [],
  "validation_status": "PASS"
}
```

---

## 11. CLI Specification

| CLI                                                | Purpose                                                 | Inputs                                                                                                                          | Outputs                                                            | Exit Code                                           | Safety Notes                                                    | Acceptance Command                                                                                                                                                                             |
| -------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ | --------------------------------------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/generate_strategy_experiment_registry.py` | Generate deterministic strategy registry                | `--output-dir`, `--strategies`                                                                                                  | `strategy_registry.json`                                           | `0` PASS, `1` validation fail, `2` safety violation | Must reject unsafe strategy; no network; no exchange            | `python3 scripts/generate_strategy_experiment_registry.py --output-dir /tmp/multi_strategy_research_workbench --strategies breakout,mean_reversion,momentum,volatility_compression`            |
| `scripts/run_parameter_search_lab.py`              | Expand bounded parameter search spaces                  | `--registry`, `--output-dir`, `--search-budget`                                                                                 | `parameter_search.json`                                            | `0` PASS, `1` schema fail, `2` budget/safety fail   | Must enforce bounded ranges and budget                          | `python3 scripts/run_parameter_search_lab.py --registry /tmp/multi_strategy_research_workbench/strategy_registry.json --output-dir /tmp/multi_strategy_research_workbench --search-budget 120` |
| `scripts/compare_strategy_research_results.py`     | Compare matrix results and generate overlap/OOS summary | `--results`, `--output-dir`                                                                                                     | `comparison.json`, `promotion_recommendations.json`                | `0` PASS, `1` invalid input, `2` safety fail        | Must not imply live readiness                                   | `python3 scripts/compare_strategy_research_results.py --results /tmp/multi_strategy_research_workbench/results.json --output-dir /tmp/multi_strategy_research_workbench`                       |
| `scripts/build_multi_strategy_research_bundle.py`  | Build bundle, artifact index, manifest, reports         | `--input-dir`, `--output-dir`                                                                                                   | `artifact_index.json`, `report.md`, `report.html`, `manifest.json` | `0` PASS, `1` missing artifact, `2` safety fail     | Must validate release_hold HOLD and sha256                      | `python3 scripts/build_multi_strategy_research_bundle.py --input-dir /tmp/multi_strategy_research_workbench --output-dir /tmp/multi_strategy_research_workbench`                               |
| `scripts/run_multi_strategy_research_workbench.py` | End-to-end pipeline orchestration                       | `--fixture-dir`, `--output-dir`, `--strategies`, `--symbols`, `--timeframes`, `--split-mode`, `--search-budget`, `--chunk-size` | all required artifacts                                             | `0` PASS, `1` functional fail, `2` safety fail      | No live, no submit, no exchange, no runtime/planner, no network | Full command in Section 17                                                                                                                                                                     |

---

## 12. Artifact Specification

Final output directory:

```text
/tmp/multi_strategy_research_workbench
```

Required artifacts:

```text
strategy_registry.json
parameter_search.json
matrix.json
results.json
portfolio_summary.json
comparison.json
promotion_recommendations.json
artifact_index.json
report.md
report.html
manifest.json
```

### 12.1 `strategy_registry.json`

Must contain:

* registered strategies；
* rejected strategies；
* validation status；
* safety flags；
* release_hold。

### 12.2 `parameter_search.json`

Must contain:

* search budget；
* expanded combinations；
* evaluated combinations；
* budget truncation flag；
* overfit warning；
* parameter sets；
* deterministic ordering。

### 12.3 `matrix.json`

Must contain:

* matrix rows；
* strategy；
* symbol；
* timeframe；
* split；
* parameter set；
* fixture path；
* release_hold；
* safety flags。

### 12.4 `results.json`

Must contain:

* per matrix row result；
* data quality；
* signal count；
* trade count；
* scorecard；
* warnings；
* safety flags。

### 12.5 `portfolio_summary.json`

Must contain:

* aggregate across symbols；
* aggregate across timeframes；
* aggregate across strategies；
* equity curve approximation；
* drawdown aggregation；
* exposure aggregation；
* trade overlap summary。

### 12.6 `comparison.json`

Must contain:

* strategy ranking；
* strategy family summary；
* timeframe summary；
* symbol summary；
* overlap analysis；
* out-of-sample scoring；
* warnings。

### 12.7 `promotion_recommendations.json`

Must contain statuses:

```text
PROMOTE_TO_NEXT_RESEARCH_ROUND
WATCH_MORE_DATA
REJECT_OVERFIT
REJECT_DRAWDOWN
HUMAN_REVIEW_REQUIRED
KEEP_HOLD
```

Every recommendation must retain:

```text
release_hold = HOLD
```

### 12.8 `artifact_index.json`

Must contain:

* artifact id；
* type；
* path；
* sha256；
* size bytes；
* related strategy；
* related experiment；
* created_by；
* release_hold；
* safety flags。

### 12.9 `report.md`

Human-readable Markdown report.

Must include:

* summary；
* strategies；
* parameter search；
* results；
* portfolio；
* comparison；
* promotion；
* safety；
* manifest summary；
* stop status。

### 12.10 `report.html`

Static HTML report.

Requirements:

* no external assets；
* no remote JS；
* no remote CSS；
* no remote fonts；
* deterministic；
* local only。

### 12.11 `manifest.json`

Manifest must contain:

```json
{
  "release_hold": "HOLD",
  "no_live": true,
  "no_submit": true,
  "no_exchange": true,
  "no_runtime_integration": true,
  "no_planner_integration": true,
  "no_network": true,
  "sha256": {},
  "artifact_sizes": {},
  "generated_by": "scripts/run_multi_strategy_research_workbench.py"
}
```

No timestamp unless explicitly passed.

Manifest must fail validation if:

* `release_hold != HOLD`；
* any safety flag is false；
* any required artifact missing；
* sha256 mismatch；
* remote URI detected；
* forbidden file path detected；
* runtime/planner/exchange/live/submit string appears as executable dependency。

---

## 13. Architecture

The architecture must be layered as follows.

### 13.1 Fixture Layer

Responsibilities:

* read local OHLCV fixture files；
* chunked reading；
* data quality validation；
* no full large CSV load；
* no network；
* no external source。

### 13.2 Historical OHLCV Lab Reuse Layer

Responsibilities:

* reuse safe offline historical backtest utilities；
* reuse simulator / scorecard where safe；
* preserve existing behavior；
* avoid unsafe imports。

### 13.3 Strategy Interface Layer

Responsibilities:

* define `StrategyDefinition`；
* define signal contract；
* define parameter schema；
* validate adapter safety。

### 13.4 Strategy Registry Layer

Responsibilities:

* register adapters；
* validate adapters；
* reject unsafe adapters；
* export deterministic registry。

### 13.5 Parameter Search Layer

Responsibilities:

* expand named presets；
* run grid search；
* enforce bounds；
* enforce budget；
* generate parameter sets。

### 13.6 Matrix Layer

Responsibilities:

* combine strategies, symbols, timeframes, splits, parameter sets；
* create deterministic `matrix_row_id`；
* write `matrix.json`。

### 13.7 Simulation / Evaluation Layer

Responsibilities:

* run signal generation；
* run offline trade simulation；
* compute metrics；
* compute scorecard；
* attach warnings。

### 13.8 Portfolio Aggregation Layer

Responsibilities:

* aggregate results across strategies/symbols/timeframes；
* estimate equity curve；
* estimate drawdown；
* summarize exposure；
* summarize overlap。

### 13.9 Comparison Layer

Responsibilities:

* rank strategies；
* compare families；
* compare timeframes；
* compare symbols；
* compute relative performance；
* detect low sample confidence。

### 13.10 Promotion Policy Layer

Responsibilities:

* convert metrics into promotion status；
* apply overfit/degradation/drawdown penalties；
* keep release_hold；
* mark human review when needed。

### 13.11 Artifact Index Layer

Responsibilities:

* enumerate artifacts；
* compute sha256；
* compute sizes；
* record related strategy/experiment；
* verify local paths。

### 13.12 Renderer Layer

Responsibilities:

* render Markdown；
* render JSON；
* render static HTML；
* no external assets；
* no timestamp unless passed。

### 13.13 Bundle Layer

Responsibilities:

* gather artifacts；
* validate required outputs；
* write manifest；
* validate safety flags；
* validate sha256。

### 13.14 CLI Orchestration Layer

Responsibilities:

* expose end-to-end CLI；
* coordinate all layers；
* fail fast on safety violation；
* return deterministic exit codes。

---

## 14. Phase Plan

### Phase 01 — T4201-T4230 Strategy Interface Foundation

Task range: `T4201-T4230`

Objective:

* Define strategy interface dataclasses and validation contracts.

Files expected:

```text
core/strategy_research_interface.py
tests/unit/test_strategy_research_interface.py
```

Tests expected:

* strategy definition validation；
* missing field rejection；
* required bar fields validation；
* safety flags required。

Acceptance criteria:

* valid strategy passes；
* unsafe strategy fails；
* no network/exchange imports；
* tests pass。

Stop condition:

* stop if implementation touches frozen files or imports live/testnet modules。

### Phase 02 — T4231-T4260 Strategy Parameter Schema

Objective:

* Define bounded parameter schema.

Files expected:

```text
core/strategy_research_parameters.py
tests/unit/test_strategy_research_parameters.py
```

Tests expected:

* bounded numeric parameters；
* enum parameters；
* missing min/max rejection；
* deterministic ordering。

Acceptance criteria:

* unbounded parameter rejected；
* schema serializes deterministically。

Stop condition:

* stop if parameter search can create infinite combinations。

### Phase 03 — T4261-T4290 Strategy Registry Core

Objective:

* Implement registry register/list/validate/export.

Files expected:

```text
core/strategy_registry_core.py
tests/unit/test_strategy_registry_core.py
scripts/generate_strategy_experiment_registry.py
```

Tests expected:

* register valid strategy；
* reject unsafe strategy；
* deterministic JSON export；
* CLI output.

Acceptance criteria:

* `strategy_registry.json` generated locally；
* no unsafe adapter accepted。

Stop condition:

* stop if registry allows exchange/live/runtime/planner dependency。

### Phase 04 — T4291-T4320 Breakout Adapter Reuse

Objective:

* Implement breakout adapter using safe local logic.

Files expected:

```text
core/strategy_research_breakout.py
tests/unit/test_strategy_research_breakout.py
```

Tests expected:

* breakout signal generation；
* cooldown behavior；
* required fields；
* deterministic signals。

Acceptance criteria:

* breakout adapter outputs `StrategySignal`；
* no order payload emitted。

Stop condition:

* stop if adapter imports frozen files。

### Phase 05 — T4321-T4350 Mean Reversion Adapter

Objective:

* Implement mean reversion adapter.

Files expected:

```text
core/strategy_research_mean_reversion.py
tests/unit/test_strategy_research_mean_reversion.py
```

Tests expected:

* z-score signal；
* no signal below threshold；
* null/std-zero safety；
* deterministic output。

Acceptance criteria:

* adapter registered；
* bounded schema；
* safe signal output。

Stop condition:

* stop if short behavior is assumed without explicit declaration。

### Phase 06 — T4351-T4380 Momentum Continuation Adapter

Objective:

* Implement momentum continuation adapter.

Files expected:

```text
core/strategy_research_momentum.py
tests/unit/test_strategy_research_momentum.py
```

Tests expected:

* momentum threshold；
* EMA alignment；
* slope filter；
* deterministic signal id。

Acceptance criteria:

* adapter emits research-only signals；
* parameter schema bounded。

Stop condition:

* stop if adapter depends on runtime scanner。

### Phase 07 — T4381-T4410 Volatility Compression Adapter

Objective:

* Implement volatility compression breakout adapter.

Files expected:

```text
core/strategy_research_volatility_compression.py
tests/unit/test_strategy_research_volatility_compression.py
```

Tests expected:

* compression detection；
* breakout confirmation；
* volume expansion optional；
* no false signal in non-compression fixture。

Acceptance criteria:

* adapter registered and validated；
* no exchange dependency。

Stop condition:

* stop if logic requires real-time data。

### Phase 08 — T4411-T4440 Adapter Registry Integration

Objective:

* Register all four adapters.

Files expected:

```text
core/strategy_registry_adapters.py
tests/unit/test_strategy_registry_adapters.py
```

Tests expected:

* all adapters registered；
* deterministic order；
* unsafe adapter rejection；
* registry JSON golden output。

Acceptance criteria:

* registry includes exactly requested strategies；
* safety flags present。

Stop condition:

* stop if registry auto-discovers unsafe modules。

### Phase 09 — T4441-T4470 Parameter Search Space

Objective:

* Build search space model and presets.

Files expected:

```text
core/parameter_search_space.py
tests/unit/test_parameter_search_space.py
```

Tests expected:

* named presets；
* finite values；
* validation errors；
* stable parameter set ids。

Acceptance criteria:

* each strategy has conservative/balanced/aggressive seed presets；
* all ranges bounded。

Stop condition:

* stop if parameter range lacks guard。

### Phase 10 — T4471-T4500 Parameter Search Engine

Objective:

* Implement deterministic grid search.

Files expected:

```text
core/parameter_search_engine.py
tests/unit/test_parameter_search_engine.py
scripts/run_parameter_search_lab.py
```

Tests expected:

* grid expansion；
* deterministic ordering；
* budget truncation；
* JSON output。

Acceptance criteria:

* `parameter_search.json` generated；
* search budget enforced。

Stop condition:

* stop if expanded combinations exceed budget without warning or truncation。

### Phase 11 — T4501-T4530 Search Budget Guard

Objective:

* Add explicit guard and negative tests.

Files expected:

```text
core/parameter_search_guard.py
tests/unit/test_parameter_search_guard.py
```

Tests expected:

* strict mode fail；
* default truncation；
* overfit warning；
* small fixture warning。

Acceptance criteria:

* budget bypass impossible；
* guard included in report.

Stop condition:

* stop if parameter search can bypass `--search-budget`。

### Phase 12 — T4531-T4560 Walk-Forward Split Adapter

Objective:

* Reuse or wrap safe walk-forward split logic.

Files expected:

```text
core/research_workbench_splits.py
tests/unit/test_research_workbench_splits.py
```

Tests expected:

* rolling split；
* deterministic split ids；
* train/validation/test fields；
* small data warning。

Acceptance criteria:

* split-mode rolling works；
* no existing behavior broken。

Stop condition:

* stop if implementation mutates historical lab files unnecessarily。

### Phase 13 — T4561-T4590 Multi-Strategy Matrix Builder

Objective:

* Build matrix across strategy/symbol/timeframe/split/parameter set.

Files expected:

```text
core/multi_strategy_matrix.py
tests/unit/test_multi_strategy_matrix.py
```

Tests expected:

* row id deterministic；
* matrix size；
* fixture path mapping；
* missing fixture handling。

Acceptance criteria:

* `matrix.json` generated；
* stable order。

Stop condition:

* stop if matrix requires downloading data。

### Phase 14 — T4591-T4620 Fixture Data Quality Layer

Objective:

* Validate local OHLCV fixture quality.

Files expected:

```text
core/research_workbench_data_quality.py
tests/unit/test_research_workbench_data_quality.py
```

Tests expected:

* missing fields；
* duplicate timestamps；
* non-monotonic timestamps；
* null OHLCV；
* chunked summary。

Acceptance criteria:

* data quality included in results；
* no full large file load.

Stop condition:

* stop if code loads full large CSV when chunking required。

### Phase 15 — T4621-T4650 Matrix Evaluator

Objective:

* Evaluate each matrix row.

Files expected:

```text
core/multi_strategy_evaluator.py
tests/unit/test_multi_strategy_evaluator.py
```

Tests expected:

* signal generation；
* simulator integration；
* scorecard；
* warnings propagation。

Acceptance criteria:

* `results.json` produced；
* all rows evaluated or safely skipped with reason。

Stop condition:

* stop if evaluator emits order payloads。

### Phase 16 — T4651-T4680 Portfolio Aggregation

Objective:

* Aggregate strategy results at portfolio level.

Files expected:

```text
core/portfolio_research_aggregation.py
tests/unit/test_portfolio_research_aggregation.py
```

Tests expected:

* aggregate expectancy；
* aggregate drawdown；
* exposure summary；
* equity curve approximation。

Acceptance criteria:

* `portfolio_summary.json` generated；
* report states approximation limitation。

Stop condition:

* stop if aggregation claims live allocation readiness。

### Phase 17 — T4681-T4710 Overlap Analysis

Objective:

* Compute signal/trade overlap and concentration.

Files expected:

```text
core/portfolio_research_overlap.py
tests/unit/test_portfolio_research_overlap.py
```

Tests expected:

* signal overlap；
* trade overlap；
* same-symbol concentration；
* family concentration；
* timeframe concentration。

Acceptance criteria:

* overlap warnings generated；
* comparison includes overlap analysis。

Stop condition:

* stop if overlap calculation silently ignores missing timestamps。

### Phase 18 — T4711-T4740 Out-of-Sample Scoring

Objective:

* Score train/validation/test stability.

Files expected:

```text
core/strategy_research_oos_scoring.py
tests/unit/test_strategy_research_oos_scoring.py
```

Tests expected:

* degradation flag；
* overfit flag；
* stability penalty；
* low sample warning。

Acceptance criteria:

* scoring included in comparison；
* overfit flagged correctly。

Stop condition:

* stop if train-only result can be promoted without warning。

### Phase 19 — T4741-T4770 Promotion Policy

Objective:

* Implement promotion/rejection policy.

Files expected:

```text
core/strategy_research_promotion.py
tests/unit/test_strategy_research_promotion.py
```

Tests expected:

* promote research round；
* watch more data；
* reject overfit；
* reject drawdown；
* human review；
* keep hold。

Acceptance criteria:

* every recommendation retains `release_hold = HOLD`；
* no recommendation implies live/testnet readiness。

Stop condition:

* stop if promotion changes release hold。

### Phase 20 — T4771-T4800 Strategy Comparison CLI

Objective:

* Implement comparison CLI.

Files expected:

```text
scripts/compare_strategy_research_results.py
tests/unit/test_compare_strategy_research_results_cli.py
```

Tests expected:

* input results；
* output comparison；
* output promotion recommendations；
* invalid input fails.

Acceptance criteria:

* CLI produces `comparison.json` and `promotion_recommendations.json`。

Stop condition:

* stop if CLI reads remote path。

### Phase 21 — T4801-T4830 Report Renderers

Objective:

* Render md/json/html reports.

Files expected:

```text
core/research_workbench_report.py
tests/unit/test_research_workbench_report.py
```

Tests expected:

* Markdown renderer；
* HTML renderer；
* no external assets；
* deterministic output。

Acceptance criteria:

* `report.md` and `report.html` generated；
* no remote JS/CSS/fonts。

Stop condition:

* stop if report includes external URL dependencies。

### Phase 22 — T4831-T4860 Artifact Index

Objective:

* Build artifact index.

Files expected:

```text
core/research_artifact_index.py
tests/unit/test_research_artifact_index.py
```

Tests expected:

* sha256；
* size bytes；
* local path validation；
* forbidden path rejection。

Acceptance criteria:

* `artifact_index.json` generated；
* all required artifacts indexed。

Stop condition:

* stop if artifact path points to forbidden file or remote URI。

### Phase 23 — T4861-T4890 Manifest Builder

Objective:

* Build and validate manifest.

Files expected:

```text
core/research_workbench_manifest.py
tests/unit/test_research_workbench_manifest.py
```

Tests expected:

* release_hold HOLD；
* safety flags；
* sha256 mismatch fail；
* missing artifact fail。

Acceptance criteria:

* `manifest.json` generated and validates；
* no timestamp unless passed。

Stop condition:

* stop if manifest permits `release_hold != HOLD`。

### Phase 24 — T4891-T4920 Bundle Builder CLI

Objective:

* Implement bundle CLI.

Files expected:

```text
scripts/build_multi_strategy_research_bundle.py
tests/unit/test_build_multi_strategy_research_bundle_cli.py
```

Tests expected:

* required artifacts；
* manifest；
* index；
* reports；
* missing artifact fail。

Acceptance criteria:

* bundle builds end-to-end from existing outputs。

Stop condition:

* stop if bundle builder stages or commits files automatically。

### Phase 25 — T4921-T4950 Full Pipeline CLI

Objective:

* Implement end-to-end workbench CLI.

Files expected:

```text
scripts/run_multi_strategy_research_workbench.py
tests/unit/test_run_multi_strategy_research_workbench_cli.py
```

Tests expected:

* full CLI happy path；
* invalid strategy fail；
* missing fixture fail；
* safety flag fail；
* budget truncation visible。

Acceptance criteria:

* full acceptance command succeeds；
* all required artifacts exist。

Stop condition:

* stop if CLI invokes live/testnet/runtime/planner.

### Phase 26 — T4951-T4980 Golden Fixtures

Objective:

* Add deterministic golden fixtures and outputs.

Files expected:

```text
tests/fixtures/multi_strategy_research/*
tests/unit/test_multi_strategy_research_golden_outputs.py
```

Tests expected:

* golden registry；
* golden parameter search；
* golden matrix；
* golden manifest。

Acceptance criteria:

* golden tests pass；
* deterministic output stable。

Stop condition:

* stop if output contains nondeterministic timestamp without explicit input。

### Phase 27 — T4981-T5010 Negative Tests

Objective:

* Add negative safety and invalid input tests.

Files expected:

```text
tests/unit/test_multi_strategy_research_negative.py
```

Tests expected:

* forbidden file path；
* unsafe adapter；
* unbounded parameter；
* network flag；
* exchange flag；
* release hold changed；
* missing artifact。

Acceptance criteria:

* all negative tests fail safely。

Stop condition:

* stop if safety violation returns success.

### Phase 28 — T5011-T5040 Performance Guard

Objective:

* Add performance and chunking guard tests.

Files expected:

```text
core/research_workbench_performance_guard.py
tests/unit/test_research_workbench_performance_guard.py
```

Tests expected:

* chunk-size honored；
* max rows guard；
* no full CSV load marker；
* large fixture summary only。

Acceptance criteria:

* chunked processing enforced；
* performance warning included when needed。

Stop condition:

* stop if large CSV/JSONL/log content is loaded into context or output.

### Phase 29 — T5041-T5070 Safety Boundary Tests

Objective:

* Add explicit safety tests.

Files expected:

```text
tests/unit/test_multi_strategy_research_safety_boundary.py
```

Tests expected:

* no live；
* no submit；
* no exchange；
* no runtime；
* no planner；
* no network；
* frozen files untouched list validation。

Acceptance criteria:

* safety tests pass；
* manifest validates all flags。

Stop condition:

* stop if any safety flag false.

### Phase 30 — T5071-T5100 Documentation Sync

Objective:

* Update docs under allowed PRD/docs area.

Files expected:

```text
docs/dev_prd/multi_strategy_research_workbench_prd.md
```

Tests expected:

* documentation path validation；
* forbidden files documented；
* no TODO placeholders。

Acceptance criteria:

* PRD committed；
* no code implementation hidden in PRD commit unless intended milestone。

Stop condition:

* stop if docs edit touches frozen files.

### Phase 31 — T5101-T5130 Governance Updates

Objective:

* Add safe governance references if needed, docs-only or allowed tests-only.

Files expected:

```text
docs/dev_prd/*
tests/unit/*
```

Tests expected:

* frozen file list coverage；
* allowed path validation；
* explicit git add policy validation if existing tooling supports it。

Acceptance criteria:

* governance docs reflect Workbench safety boundaries；
* no runtime/planner changes。

Stop condition:

* stop if governance update requires modifying frozen backlog platform files outside allowed areas.

### Phase 32 — T5131-T5160 Acceptance Run

Objective:

* Run full acceptance command and artifact verification.

Files expected:

```text
/tmp/multi_strategy_research_workbench/*
```

Tests expected:

* full CLI；
* artifact verification；
* manifest validation；
* new tests；
* relevant unit suite。

Acceptance criteria:

* acceptance command exits 0；
* required artifacts exist；
* manifest PASS；
* release_hold HOLD。

Stop condition:

* stop if full pipeline incomplete due to safety risk。

### Phase 33 — T5161-T5180 Full Unit Verification

Objective:

* Run full unit suite.

Files expected:

```text
no new required files
```

Tests expected:

```text
PYTHONPATH=. .venv/bin/pytest -q
```

Acceptance criteria:

* full unit suite passes；
* no unrelated regression；
* baseline documented。

Stop condition:

* stop if full baseline breaks and cannot be isolated safely。

### Phase 34 — T5181-T5200 Closeout

Objective:

* Final closeout report and milestone commit.

Files expected:

```text
docs/dev_prd/*
```

Tests expected:

* final acceptance summary；
* git status；
* frozen files untouched；
* tracked dirty = 0 after commit。

Acceptance criteria:

* PASS/PARTIAL/FAIL clearly marked；
* T5201+ marked HUMAN_REVIEW_REQUIRED；
* release_hold remains HOLD。

Stop condition:

* stop if any attempt is made to unlock live/testnet.

---

## 15. Test Strategy

### 15.1 Unit Tests

Unit tests must cover:

* strategy interface；
* parameter schema；
* strategy registry；
* four adapters；
* parameter search；
* matrix builder；
* evaluator；
* portfolio aggregation；
* overlap analysis；
* OOS scoring；
* promotion policy；
* report renderers；
* artifact index；
* manifest；
* bundle；
* CLI parsing。

### 15.2 Fixture Tests

Fixture tests must use local files only:

```text
tests/fixtures/historical_backtest_lab
tests/fixtures/multi_strategy_research
```

Must validate:

* chunked read；
* missing fixture；
* malformed fixture；
* duplicate timestamp；
* small sample warning；
* deterministic output。

### 15.3 Golden Regression Tests

Golden tests must compare deterministic outputs:

```text
strategy_registry.json
parameter_search.json
matrix.json
portfolio_summary.json
comparison.json
manifest.json
```

Golden outputs must avoid timestamps unless explicitly passed.

### 15.4 Negative Tests

Negative tests must include:

* unsafe adapter rejected；
* unbounded parameter rejected；
* over-budget search guarded；
* missing required artifact fails；
* manifest mismatch fails；
* release_hold changed fails；
* forbidden file path fails；
* remote URI fails；
* network flag fails；
* exchange flag fails；
* runtime/planner flag fails。

### 15.5 CLI Tests

CLI tests must cover:

* valid invocation；
* invalid strategy；
* invalid fixture dir；
* invalid output dir；
* invalid split mode；
* budget too low；
* missing artifact；
* safety violation；
* deterministic exit codes。

### 15.6 Acceptance Tests

Acceptance test must run the command in Section 17 and verify artifacts.

### 15.7 Performance Guard Tests

Performance guard tests must ensure:

* chunk-size honored；
* large file not read fully；
* output summaries do not paste full CSV/JSONL/log；
* row count guard works；
* search budget prevents explosion。

### 15.8 Safety Boundary Tests

Safety boundary tests must assert:

```text
release_hold = HOLD
no_live = true
no_submit = true
no_exchange = true
no_runtime_integration = true
no_planner_integration = true
no_network = true
```

Also assert:

* forbidden files list unchanged；
* no forbidden import strings；
* no order payload fields；
* no exchange client initialization。

### 15.9 Full Unit Suite

Final verification:

```bash
PYTHONPATH=. .venv/bin/pytest -q
```

Expected:

* all new tests pass；
* full unit suite passes；
* no unrelated regression。

---

## 16. Acceptance Criteria

### 16.1 PASS

Mark PASS only if all conditions are true:

* full multi-strategy pipeline works；
* required artifacts exist；
* manifest validates；
* all new tests pass；
* full unit suite passes；
* `release_hold` remains `HOLD`；
* tracked dirty = 0 after final commit；
* frozen files untouched；
* no live；
* no submit；
* no exchange；
* no runtime integration；
* no planner integration；
* no network；
* no secrets read；
* no `git add .` used；
* all outputs are local artifacts/reports/fixtures only。

### 16.2 PARTIAL

Mark PARTIAL if:

* useful safe phases are completed；
* some expected full-pipeline functionality remains incomplete；
* no safety violation occurred；
* frozen files untouched；
* release_hold remains HOLD；
* tests for completed parts pass；
* incomplete parts are clearly documented；
* no false PASS claim made。

### 16.3 FAIL

Mark FAIL if any condition occurs:

* tests fail and cannot be isolated；
* frozen files touched；
* forbidden files imported；
* forbidden files executed；
* release_hold changed；
* live/submit/exchange boundary violated；
* runtime/planner integration attempted；
* network required；
* secrets read；
* tracked dirty remains unexpectedly；
* manifest mismatch；
* required artifact missing in claimed PASS；
* parameter search bypasses budget；
* report claims live/testnet readiness。

---

## 17. Acceptance Command

Required command:

```bash
python3 scripts/run_multi_strategy_research_workbench.py \
  --fixture-dir tests/fixtures/historical_backtest_lab \
  --output-dir /tmp/multi_strategy_research_workbench \
  --strategies breakout,mean_reversion,momentum,volatility_compression \
  --symbols BTCUSDT,ETHUSDT \
  --timeframes 5m,15m \
  --split-mode rolling \
  --search-budget 120 \
  --chunk-size 25
```

### 17.1 Artifact Verification Python Snippet

```bash
python3 - <<'PY'
from pathlib import Path
import json
import hashlib

out = Path("/tmp/multi_strategy_research_workbench")

required = [
    "strategy_registry.json",
    "parameter_search.json",
    "matrix.json",
    "results.json",
    "portfolio_summary.json",
    "comparison.json",
    "promotion_recommendations.json",
    "artifact_index.json",
    "report.md",
    "report.html",
    "manifest.json",
]

missing = [name for name in required if not (out / name).exists()]
if missing:
    raise SystemExit(f"missing artifacts: {missing}")

manifest = json.loads((out / "manifest.json").read_text())

required_flags = {
    "release_hold": "HOLD",
    "no_live": True,
    "no_submit": True,
    "no_exchange": True,
    "no_runtime_integration": True,
    "no_planner_integration": True,
    "no_network": True,
}

for key, expected in required_flags.items():
    actual = manifest.get(key)
    if actual != expected:
        raise SystemExit(f"manifest safety flag mismatch: {key}={actual!r}, expected {expected!r}")

for name in required:
    path = out / name
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if "sha256" in manifest:
        recorded = manifest["sha256"].get(name)
        if recorded and recorded != digest:
            raise SystemExit(f"sha256 mismatch for {name}")

for name in required:
    text = (out / name).read_text(errors="ignore")
    forbidden_terms = [
        "demo-fapi.binance.com",
        "fapi.binance.com",
        "api.binance.com",
        "submit_order",
        "place_order",
        "cancel_order",
        "flatten",
        "live_runner",
        "planner integration enabled",
    ]
    hits = [term for term in forbidden_terms if term in text]
    if hits:
        raise SystemExit(f"forbidden executable/safety terms found in {name}: {hits}")

print("ARTIFACT_VERIFICATION_PASS")
PY
```

### 17.2 Git Safety Verification

```bash
git status --short
```

Expected after final commit:

```text
<empty>
```

Frozen file verification:

```bash
git status --short -- \
  core/live_runner.py \
  scripts/live_playbook.py \
  scripts/submit_approved_candidates.py \
  scripts/run_testnet_order_smoke.py \
  scripts/run_signal_testnet_trial.py \
  scripts/run_spot_testnet_acceptance.py \
  scripts/safe_flatten_testnet_symbol.py \
  scripts/replay_shadow_order_plans_as_testnet_dry.py \
  scripts/submit_replayed_testnet_payload.py \
  scripts/run_controlled_testnet_shift.py \
  scripts/run_daily_shadow_scan_pipeline.py \
  scripts/run_next_shadow_experiment_plan.py \
  scripts/run_observation_shift_runtime.py \
  scripts/run_remediation_shadow_only_loop.py \
  scripts/run_replay_submit_batch.py \
  scripts/run_right_breakout_param_observation.py \
  scripts/run_right_breakout_scan_dry.py \
  scripts/run_shadow_observation_experiments.py \
  scripts/run_shadow_sample_collection_pipeline.py \
  scripts/run_shadow_universe_collector.py \
  scripts/verify_risk_release_flow.py \
  scripts/verify_testnet_repair_scenarios.py
```

Expected:

```text
<empty>
```

---

## 18. Rollout Plan

### 18.1 PRD Commit

First commit only this PRD:

```bash
git add docs/dev_prd/multi_strategy_research_workbench_prd.md
git commit -m "docs: add multi-strategy research workbench PRD"
```

Do not include implementation in PRD commit unless explicitly intended.

### 18.2 Phase Implementation

Implementation proceeds phase by phase from T4201 to T5200.

Each phase must:

* modify only allowed files；
* add tests；
* run targeted tests；
* report FILES / TESTS / RESULT / NOTES；
* commit milestone when safe；
* stop on safety violation。

### 18.3 Milestone Commits

Suggested milestone commits:

```text
strategy interface + registry
strategy adapters
parameter search
matrix + evaluator
portfolio aggregation + overlap
OOS scoring + promotion
reports + artifact index + manifest
bundle + full CLI
golden + negative + safety tests
acceptance closeout
```

Each commit must use explicit git add only.

### 18.4 Final Acceptance

Final acceptance requires:

* run full command；
* run artifact verification snippet；
* run new tests；
* run full unit suite；
* confirm frozen files untouched；
* confirm release_hold HOLD；
* confirm tracked dirty = 0。

### 18.5 T5201+ HUMAN_REVIEW_REQUIRED

At T5200 closeout:

```text
T5201+ = HUMAN_REVIEW_REQUIRED
```

No automatic continuation into testnet, runtime, planner, submit, or live.

---

## 19. Risk Register

| Risk                                             | Description                                                        | Mitigation                                                                                  |
| ------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| Accidentally touching frozen files               | Agent modifies or stages one of 22 frozen backlog files            | Keep forbidden list in PRD and tests; run git status on frozen files; explicit git add only |
| Accidental network usage                         | Adapter or CLI attempts to download data or call exchange          | Safety flags; no-network tests; reject remote URI; avoid requests/http imports              |
| Accidental full CSV load                         | Large fixture read fully into memory/context                       | Enforce chunk-size; chunked reader tests; summary-only output                               |
| Strategy adapter imports unsafe modules          | Adapter imports live/testnet/runtime/planner code                  | Registry validation; forbidden import tests; allowed path restrictions                      |
| Overfitting via parameter search                 | Search finds parameter set that only works in train sample         | Search budget; OOS scoring; degradation flag; overfit warning                               |
| False confidence from small fixtures             | Fixture too small to support robust conclusion                     | sample_size_warning; WATCH_MORE_DATA status                                                 |
| Portfolio aggregation hides single-strategy risk | Aggregate metrics look good while one strategy has severe drawdown | Per-strategy risk section; drawdown contribution summary                                    |
| Correlation/overlap calculation misleading       | Overlap approximations misrepresent true dependency                | Label as research approximation; include low sample warnings                                |
| Unstable tests                                   | Golden outputs drift due to nondeterministic ordering/timestamps   | Stable ids; sorted JSON keys; no timestamps unless passed                                   |
| Manifest mismatch                                | sha256 or artifact sizes inconsistent                              | Manifest validation; artifact verification snippet                                          |
| Report drift                                     | Markdown/HTML disagree with JSON artifacts                         | Render reports from same canonical data model                                               |
| Promotion misunderstood as live approval         | PROMOTE status interpreted as trading permission                   | Always retain release_hold HOLD; report states research-only                                |
| Runtime/planner integration creep                | Workbench starts depending on execution orchestration              | Non-goal; tests reject runtime/planner terms/imports                                        |
| Secrets exposure                                 | Code reads `.env` or API keys                                      | No secrets policy; tests reject env/key reading                                             |
| Git staging mistake                              | `git add .` stages unrelated files                                 | explicit git add only; check git status before commit                                       |

---

## 20. Stop Conditions

Implementation must stop immediately if any of the following occurs:

1. If frozen file touched, stop.
2. If release_hold changes from HOLD, stop.
3. If network is needed, stop.
4. If exchange client is needed, stop.
5. If Binance/testnet/live submit path is needed, stop.
6. If secrets / credentials / API keys are needed, stop.
7. If full test baseline breaks and cannot be isolated, stop.
8. If implementation requires runtime integration, stop.
9. If implementation requires planner integration, stop.
10. If parameter search tries to bypass search budget, stop.
11. If adapter emits order payload, stop.
12. If report claims live readiness, stop.
13. If manifest safety flags cannot validate, stop.
14. If artifact path points outside local output boundary unexpectedly, stop.
15. If `git add .` or equivalent bulk staging is required, stop.
16. If implementation requires modifying files outside allowed areas, stop.
17. If full CSV/JSONL/log must be loaded into context, stop.
18. If T5201+ work is needed, mark HUMAN_REVIEW_REQUIRED and stop.

Stop status:

```text
STOPPED_FOR_SAFETY
```

or:

```text
HUMAN_REVIEW_REQUIRED
```

---

## 21. Future Work

T5201+ possible directions:

1. Larger local datasets；
2. More strategy families；
3. Portfolio construction research；
4. Regime filter；
5. BTC dominance / market regime；
6. Position sizing research；
7. Risk parity / volatility targeting；
8. Event-driven research；
9. Better slippage modeling；
10. Better fee modeling；
11. Intraday liquidity proxy；
12. Multi-market offline research；
13. More robust walk-forward schemes；
14. Parameter stability heatmaps；
15. Strategy clustering；
16. Offline research database export；
17. Read-only review of testnet layer；
18. Human-reviewed dry-run bridge；
19. Governance review for possible future testnet research；
20. Still no live unlock without human approval。

T5201+ must remain:

```text
HUMAN_REVIEW_REQUIRED
```

No live unlock.

No automatic testnet submit.

No runtime/planner integration without new explicit PRD and human approval.

---

## 22. Future Claude Execution Prompt

```text
Use Caveman / terse engineering mode. Output only FILES / TESTS / RESULT / NOTES. No greetings. No long explanations. No unrelated code.

You are working in the quant system repository.

Read this PRD first:

docs/dev_prd/multi_strategy_research_workbench_prd.md

Implement T4201-T5200 phase by phase.

You must obey all safety boundaries in the PRD.

Hard rules:
- No network.
- No Binance.
- No exchange client.
- No testnet submit.
- No live trading.
- No order placement.
- No cancel.
- No flatten.
- No runtime integration.
- No planner integration.
- No secrets / credentials / API keys.
- release_hold must remain HOLD.
- Do not modify, import, execute, git add, or commit the 22 frozen backlog files listed in the PRD.
- Do not use git add .
- Use explicit git add only.
- Only modify files in allowed areas listed in the PRD.
- All outputs must be local fixtures / artifacts / reports only.
- Do not load full CSV/JSONL/log files into context; use head/tail/rg/chunked summaries.

Execution:
1. Start with PRD commit if not already committed.
2. Implement phases in order.
3. For each milestone:
   - list FILES
   - run targeted TESTS
   - report RESULT
   - include NOTES for warnings or partials
   - commit safe milestone with explicit git add only
4. Run the required acceptance command from Section 17.
5. Run artifact verification snippet from Section 17.
6. Run full unit suite:
   PYTHONPATH=. .venv/bin/pytest -q
7. Verify frozen files untouched.
8. Verify release_hold remains HOLD.
9. Verify tracked dirty = 0 after final commit.
10. Stop at T5200.
11. Mark T5201+ as HUMAN_REVIEW_REQUIRED.
12. Do not continue into live/testnet/runtime/planner work.

Required final output format:

FILES
- ...

TESTS
- ...

RESULT
- PASS / PARTIAL / FAIL

NOTES
- ...
```

