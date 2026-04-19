已按要求只修改两个测试文件：

- [tests/unit/test_execution.py](/Users/winnie/Documents/trae_projects/qq/tests/unit/test_execution.py)
- [tests/unit/test_order_manager.py](/Users/winnie/Documents/trae_projects/qq/tests/unit/test_order_manager.py)

`test_execution.py` 现在不再严格比较 `result.keys()`，改为保留旧字段兼容断言，并新增对 `reference_entry_price`、`entry_fill_price`、`entry_fee`、`total_fees`、`leverage`、`margin_required` 的校验。

`test_order_manager.py` 现在按当前 dry-run 真实行为校验平仓后的统一交易经济字段，包括 `reference_exit_price`、`exit_fill_price`、`exit_fee`、`total_fees`、`reference_gross_pnl`、`gross_pnl`、`slippage_cost`、`net_pnl`，同时保留对兼容字段 `exit_price`、`pnl`、`fees_paid` 的断言；没有修改任何业务代码。

验证结果：
- `./.venv/bin/python -m pytest tests/unit/test_execution.py -v` 通过
- `./.venv/bin/python -m pytest tests/unit/test_order_manager.py -v` 通过
