# TASKS

## T001 项目骨架初始化
目标：
- 建立量化系统目录结构
- 明确核心模块边界
- 保证项目可以启动

验收：
- 存在 core / utils / config 等模块
- 存在 main.py
- 存在 requirements.txt
- 存在基础配置文件
- 项目可以成功执行基础启动命令

---

## T002 配置系统
目标：
- 支持从 yaml / env 加载配置
- 区分 dry-run 与 live 模式

验收：
- 可读取 config.yaml
- 可读取环境变量
- 缺少关键配置时给出明确报错

---

## T201 execution.py 单元测试
目标：
- 为 execution.py 添加最小单元测试
- 只测试 dry-run 模式
- 只测试 open_short 方法

验收：
- 创建 tests/unit/test_execution.py
- 测试 dry-run 开仓成功场景
- 测试 quantity <= 0 边界条件
- 所有测试通过

状态：✅ 完成 (2026-04-17)

---

## T202 risk_manager.py 单元测试
目标：
- 为 risk_manager.py 添加最小单元测试
- 只测试 can_open_new_trade() 方法
- 只测试 calculate_position() 方法

验收：
- 创建 tests/unit/test_risk_manager.py
- 测试权限检查的所有允许/拒绝条件
- 测试仓位计算和边界调整
- 所有测试通过

状态：✅ 完成 (2026-04-18)

---

## T203 order_manager.py 单元测试
目标：
- 为 order_manager.py 添加最小单元测试
- 只测试状态流转方法
- 只测试止损止盈触发逻辑

验收：
- 创建 tests/unit/test_order_manager.py
- 测试 has_position/can_open/open_position 状态变化
- 测试 update_market 的止损/止盈触发
- 所有测试通过

状态：✅ 完成 (2026-04-18)

---

## T003 日志系统
目标：
- 建立统一日志模块
- 支持控制台输出与文件落盘

验收：
- 启动后能生成日志
- 错误信息可追踪
