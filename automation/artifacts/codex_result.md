在 [tests/unit/test_execution.py](/Users/winnie/Documents/trae_projects/qq/tests/unit/test_execution.py:1) 添加了最小版 dry-run 单元测试，只覆盖你指定的两类场景。

`test_dry_run_open_short_success` 校验了 `open_short` 在 dry-run 下的完整返回结构和关键数值，包括 `accepted/mode/symbol/entry_price/stop_price/take_profit_price/quantity/notional/fees_paid/fee_rate/meta/notes/execution_duration`。`test_open_short_invalid_quantity_rejected` 用参数化覆盖了 `quantity=0.0` 和 `quantity=-0.5`，并验证返回 `{"accepted": False, "reason": "invalid_quantity"}`，同时断言 warning 被记录，且不会触发 live 分支调用。

验证结果：
- `PYTHONPYCACHEPREFIX=/tmp/pycache ./.venv/bin/python -m py_compile tests/unit/test_execution.py` 通过。
- 手动执行 `ExecutionEngine.open_short(...)` 的 dry-run 成功路径和非法数量路径，返回值与测试断言一致。
- `pytest tests/unit/test_execution.py -v` 目前无法在这个会话里执行，因为系统 Python 和仓库 `.venv` 都没有安装 `pytest`，报错是 `No module named pytest`。如果你补装 `pytest`，这个文件就可以按你给的命令直接跑。
