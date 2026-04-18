已新增单测 [tests/unit/test_order_manager.py](/Users/winnie/Documents/trae_projects/qq/tests/unit/test_order_manager.py)，只覆盖你要求的最小范围：初始状态、`open_position()` 后的状态切换，以及 `dry-run` 模式下 `update_market()` 的止损/止盈/无触发逻辑。断言内容直接对齐 `core/order_manager.py` 当前实现，包括持仓字段、平仓返回结构和 `pnl`/`fees_paid`/`return_pct` 计算。

验证已完成，未修改 `core/order_manager.py` 或其他源码文件。当前环境没有全局 `pytest`，所以我用仓库虚拟环境执行了：
```bash
./.venv/bin/python -m pytest tests/unit/test_order_manager.py --collect-only
./.venv/bin/python -m pytest tests/unit/test_order_manager.py -v
```
结果是 `6 passed in 0.06s`。
