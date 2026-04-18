# Learnings

## Project-Specific Learnings

### Technical Decisions
*(Learnings about technical choices, architecture decisions)*

### Pattern Library
*(Reusable patterns discovered in this project)*

### Anti-Patterns
*(Patterns to avoid based on project experience)*

### External Dependencies
*(Learnings about external APIs, libraries, services)*

---

## Template for New Learnings

```markdown
## [Date] Learning Category

### Observation
[What happened or was discovered]

### Impact
[Why this matters]

### Recommendation
[What to do about it]

### Related Files
- [file paths involved]

### Example
[if applicable]
```

---

## 2026-04-17 T201 Task Execution

### Observation
execution.py 作为第一波接管模块完全符合当前阶段约束：
- 已实现完整的 dry-run 模式
- 无外部 API 依赖（exchange 仅用于 live 模式）
- 模块职责清晰、边界明确
- 逻辑简单、易于理解

### Impact
- 验证了测试框架建立的可行性
- 为后续模块测试提供了模板
- 证明当前仓库结构支持增量测试开发

### Recommendation
1. 优先测试已有 dry-run 模式的模块（execution、risk_manager、order_manager）
2. 使用步化任务单（先读源码再适配）比硬编码更安全
3. 测试任务不修改源码，降低回归风险

### Related Files
- core/execution.py
- tests/unit/test_execution.py
- automation/current_task.md

---

## 2026-04-18 T202 Task Execution

### Observation
risk_manager.py 作为第二波接管模块完全符合当前阶段约束：
- 纯计算逻辑，无外部依赖
- 无模块间强依赖
- 状态管理清晰
- 方法职责单一，易于测试

### Impact
- 验证了风控逻辑的测试可行性
- 参数化测试有效覆盖多场景（9个测试用例）
- 证明了风险计算模块的独立性和可测试性

### Recommendation
1. 继续测试其他纯逻辑模块（order_manager、signal_engine）
2. 参数化测试是覆盖多场景的有效方法
3. 先读源码理解实际逻辑再写测试，避免硬编码假设

### Related Files
- core/risk_manager.py
- tests/unit/test_risk_manager.py
- automation/current_task.md

---

## 2026-04-18 T203 Task Execution

### Observation
order_manager.py 作为第三波接管模块完全符合当前阶段约束：
- 纯状态管理，无外部依赖
- dry-run 模式的平仓逻辑可独立测试
- 状态流转清晰（无持仓 -> 持仓 -> 平仓）
- 止损止盈触发条件明确

### Impact
- 验证了状态管理模块的测试可行性
- fixtures 对于复杂测试数据很有效
- 证明了 order_manager 在 dry-run 下的完全可测试性
- 为测试持仓状态流转建立了标准模式

### Recommendation
1. 继续测试 remaining 模块（signal_engine、data_feed）
2. fixture 复用模式在测试 suite 之间很有价值
3. 状态机逻辑需要测试所有状态转换路径

### Related Files
- core/order_manager.py
- tests/unit/test_order_manager.py
- automation/current_task.md

---

## 2026-04-18 T204 Task Execution

### Observation
signal_engine.py 作为第四波接管模块符合当前阶段约束：
- 无外部 API 依赖
- 状态机逻辑相对独立
- 复杂度高（5种状态、多指标计算）

### Impact
- 验证了复杂状态机模块的测试可行性
- 非信号路径测试有效降低测试复杂度
- 避免指标精确断言提升了测试稳定性
- 证明了分阶段测试策略的有效性

### Recommendation
1. 对于复杂模块，优先测试非关键路径（NONE返回）
2. 避免对依赖模块做精确断言（如indicators.py）
3. 状态机测试应覆盖所有状态转换路径
4. 后续可补充信号触发路径作为独立任务

### Related Files
- core/signal_engine.py
- tests/unit/test_signal_engine.py
- automation/current_task.md

---

## Initial Context

### Project Phase
- Current: Stage 0 - Project Skeleton
- Focus: Structure, Testability, Risk Control
- Default Mode: dry-run

### Key Constraints
- No real orders without explicit permission
- No hardcoded secrets
- All code must be testable in dry-run
- Configuration-driven behavior

### Technology Stack
- Python 3.11+
- Binance API (planned)
- YAML configuration
- System logger
