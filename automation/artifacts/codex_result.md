新增了 [tests/unit/test_risk_manager.py](/Users/winnie/Documents/trae_projects/qq/tests/unit/test_risk_manager.py)，只覆盖 `RiskManager.can_open_new_trade` 和 `RiskManager.calculate_position`。测试按源码真实行为写了 9 个参数化场景：5 个权限检查返回值，4 个仓位计算场景，其中“无效风险距离”按实现实际只覆盖了 `entry == stop`，因为源码先做了 `abs(stop - entry)`，不存在单独的“负风险距离”分支。

验证已完成，使用仓库虚拟环境运行：
```bash
./.venv/bin/python -m pytest tests/unit/test_risk_manager.py --collect-only
./.venv/bin/python -m pytest tests/unit/test_risk_manager.py -v
```
结果是 `9 passed`。本次只新增了目标测试文件；`git status` 里还有一些仓库中原本就存在的未提交改动，但没有修改 `core/risk_manager.py` 或其他受限文件。
