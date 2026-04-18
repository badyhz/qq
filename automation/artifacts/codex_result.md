已创建 [tests/REGRESSION.md](/Users/winnie/Documents/trae_projects/qq/tests/REGRESSION.md)，内容按要求写入，4 个核心测试文件与 `./.venv/bin/python` 回归命令都已列出，`tests/conftest.py` 未创建。

验证结果：
- `./.venv/bin/python -m pytest tests/unit/ -v` 通过，收集 24 项测试，`24 passed`
- `./.venv/bin/python -m pytest tests/unit/test_execution.py -v` 通过，`3 passed`
- `./.venv/bin/python -m pytest tests/unit/test_risk_manager.py -v` 通过，`9 passed`
- `./.venv/bin/python -m pytest tests/unit/test_order_manager.py -v` 通过，`6 passed`
- `./.venv/bin/python -m pytest tests/unit/test_signal_engine.py -v` 通过，`6 passed`

工作区核对后，新增文件只有 [tests/REGRESSION.md](/Users/winnie/Documents/trae_projects/qq/tests/REGRESSION.md)；已有的 `automation/artifacts/codex_result.md` 和 `automation/current_task.md` 是原本就存在的未提交改动，我没有修改源码文件或现有测试文件。
