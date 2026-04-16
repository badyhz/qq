# ARCHITECTURE

## 总体目标
构建一个面向 Binance 的量化交易系统，采用模块化架构，先 dry-run，后逐步接入真实交易。

## 核心模块
1. data_feed
   - 行情数据接入
   - WebSocket / REST

2. signal_engine
   - 交易信号生成
   - 指标计算
   - 状态机判断

3. risk_manager
   - 仓位控制
   - 最大风险限制
   - 止损止盈参数管理

4. execution
   - 下单执行
   - dry-run / live 统一接口

5. order_manager
   - 订单状态跟踪
   - 挂单、撤单、补单逻辑

6. trade_logger
   - 成交记录
   - 信号记录
   - 行为审计

## 推荐目录结构
- main.py
- config.yaml
- core/
- utils/
- tests/
- logs/

## 第一阶段原则
- 先有骨架，再补策略
- 先能跑通，再做优化
- 先做安全，再做速度
