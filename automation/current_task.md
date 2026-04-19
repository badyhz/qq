### T207c
请只修改测试文件，使其适配新的 dry-run 统一交易经济字段。
只允许修改：
- tests/unit/test_execution.py
- tests/unit/test_order_manager.py
禁止修改：
- core/**
- config.yaml
- main.py
- tests/unit/test_risk_manager.py
- tests/unit/test_signal_engine.py
- 其他任何文件
要求：
1. 更新 test_execution.py：
   - 不再严格比较 result.keys() 的完全相等
   - 改为断言旧字段仍存在且值兼容
   - 新增断言以下字段存在且合理：
     - reference_entry_price
     - entry_fill_price
     - entry_fee
     - total_fees
     - leverage
     - margin_required
2. 更新/补充 test_order_manager.py：
   - 验证 dry-run 平仓后的新字段：
     - reference_exit_price
     - exit_fill_price
     - exit_fee
     - total_fees
     - reference_gross_pnl
     - gross_pnl
     - slippage_cost
     - net_pnl
   - 同时断言兼容字段：
     - exit_price
     - pnl
     - fees_paid
3. 所有断言必须基于当前源码真实行为
4. 不要修改业务代码
5. 完成后运行：
   - ./.venv/bin/python -m pytest tests/unit/test_execution.py -v
   - ./.venv/bin/python -m pytest tests/unit/test_order_manager.py -v
