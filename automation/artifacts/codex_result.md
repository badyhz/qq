已新增单测 [tests/unit/test_signal_engine.py](/Users/winnie/Documents/trae_projects/qq/tests/unit/test_signal_engine.py)，只覆盖你要求的最小范围：基础状态流转（`IDLE` / `IN_POSITION` / `COOLDOWN`）和 `on_candle` 的非信号路径，没有触碰 `core/signal_engine.py` 或其他文件。

验证结果正常。由于系统 PATH 里没有 `pytest`，我是用仓库虚拟环境执行的等价命令：
```bash
./.venv/bin/python -m pytest tests/unit/test_signal_engine.py --collect-only
./.venv/bin/python -m pytest tests/unit/test_signal_engine.py -v
```
结果是 `6 collected`，`6 passed`。
