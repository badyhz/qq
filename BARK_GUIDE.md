# Bark 消息推送使用指南

## 概述

Bark 是一款 iOS 消息推送工具，可以将量化交易系统的实时状态推送到您的 iPhone 上。系统会在以下情况自动发送通知：

1. **错误检测** - 当系统发生错误时
2. **交易平仓** - 当交易结束时（止盈/止损/超时等）
3. **交易信号** - 当发现新的交易机会时
4. **系统状态** - 定期推送系统运行状态（可选）

## 配置方法

### 1. 安装 Bark

在 iPhone 上从 App Store 下载并安装 Bark 应用。

### 2. 获取设备密钥

打开 Bark 应用，您会看到一个密钥（Device Key），类似于：`qQH2uNcLvpFuqfHqykmMCD`

### 3. 修改配置文件

编辑 `config.yaml` 文件中的 `bark` 配置部分：

```yaml
bark:
  enabled: true  # 是否启用 Bark 推送
  device_key: "YOUR_DEVICE_KEY"  # 替换为您的 Bark 设备密钥
  notify_on_error: true  # 错误时推送
  notify_on_trade: true  # 交易平仓时推送
  notify_on_signal: true  # 发现交易信号时推送
  notify_on_status: false  # 定期状态推送（默认关闭）
  error_cooldown_minutes: 10  # 错误推送冷却时间
  trade_cooldown_minutes: 5  # 交易推送冷却时间
  status_interval_hours: 6  # 状态推送间隔
```

## 通知类型与策略

### 1. 错误通知（强提醒）

**触发条件**：
- 任何 ERROR 级别的日志
- WebSocket 连接失败
- 数据获取失败
- 交易执行错误
- 其他系统异常

**提醒特征**：
- 🔴 级别：`critical`（重要警告）
- 🔊 声音：`alarm`（警报声）
- 🔉 音量：10（最大音量）
- 📱 即使手机静音也会响铃

**示例**：
```
⚠️ 系统错误：data_feed - _on_error
模块：data_feed
函数：_on_error
文件：/root/qq/core/data_feed.py
行号：227
时间：2026-04-14 02:17:32
异常：ConnectionError: Connection lost
```

### 2. 交易平仓通知（强提醒）

**触发条件**：
- 止盈离场（take_profit）
- 止损离场（stop_loss）
- 超时平仓（timeout）
- 保本离场（breakeven）
- 反向信号平仓（opposite_signal）
- 风控平仓（risk_management）

**提醒特征**：
- 🎯 级别：`critical`
- 🔊 声音：`alarm`
- 🔉 音量：10
- 💰 包含盈亏信息

**示例**：
```
✅ TP: BTCUSDT
✅ 盈亏：+12.50 USDT
退出原因：take_profit
评分：8
持续时间：145 秒
```

### 3. 交易信号通知（强提醒）

**触发条件**：
- 检测到新的交易信号
- 信号评分达到阈值
- 风控检查通过

**提醒特征**：
- 🎯 级别：`critical`
- 🔊 声音：`alarm`
- 🔉 音量：10
- 📊 包含信号详情

**示例**：
```
🎯 狙击指令：BTCUSDT
信号类型：SHORT
评分：8

建议入场价：72141.40
止损价：72285.60
止盈价：71854.20
仓位：0.0035 BTC
```

### 4. 系统启动通知（主动提醒）

**触发条件**：
- 系统成功启动

**提醒特征**：
- 🤖 级别：`active`
- 🔊 声音：`success`
- 📱 常规推送

**示例**：
```
🤖 量化系统启动
模式：dry-run
交易对：BTCUSDT
周期：5m
Python: 3.11.6
启动时间：2026-04-14T02:16:31.980285+00:00
```

## 冷却机制

为了避免频繁推送打扰用户，系统实现了智能冷却机制：

### 错误通知冷却
- **默认冷却时间**：10 分钟
- **机制**：10 分钟内的多个错误只推送第一个
- **统计**：冷却期内的错误数量会被记录并在下次推送时告知

### 交易通知冷却
- **默认冷却时间**：5 分钟
- **机制**：5 分钟内的多笔交易只推送第一笔
- **原因**：避免连续交易造成通知轰炸

### 状态通知冷却
- **默认间隔**：6 小时
- **机制**：每 6 小时最多推送一次状态

## 自定义配置

### 完全关闭某类通知

```yaml
bark:
  enabled: true
  notify_on_error: false  # 关闭错误推送
  notify_on_trade: false  # 关闭交易推送
  notify_on_signal: false  # 关闭信号推送
  notify_on_status: false  # 关闭状态推送
```

### 调整冷却时间

```yaml
bark:
  error_cooldown_minutes: 30  # 错误冷却 30 分钟
  trade_cooldown_minutes: 10  # 交易冷却 10 分钟
  status_interval_hours: 12  # 状态 12 小时推送一次
```

### 关闭所有推送

```yaml
bark:
  enabled: false  # 完全禁用 Bark
```

## 通知分组

Bark 支持消息分组，系统已配置以下分组：

- **system** - 系统通知（启动、关闭等）
- **errors** - 错误通知
- **trades** - 交易通知
- **signals** - 信号通知
- **status** - 状态通知
- **daily** - 每日报告

您可以在 Bark 应用中按分组管理通知。

## 故障排查

### 问题 1：收不到推送

**检查步骤**：
1. 确认 `config.yaml` 中 `bark.enabled: true`
2. 确认 `device_key` 正确
3. 检查手机网络连接
4. 查看日志文件：`logs/bot.log`
5. 查看 Bark 应用是否正常运行

**日志示例**：
```
Bark notification sent | title=system
Bark API returned error | code=400 | message=Invalid device key
```

### 问题 2：推送过于频繁

**解决方案**：
1. 增加冷却时间
2. 关闭不需要的通知类型
3. 检查是否有持续性错误

### 问题 3：推送声音太小

**解决方案**：
1. 检查手机音量设置
2. 确认 Bark 应用的通知权限已开启
3. 检查是否开启了静音模式（强提醒应该能突破静音）

## 高级用法

### 自定义推送声音

Bark 支持多种提示音：
- `alarm` - 警报声（最响亮）
- `bell` - 铃声
- `success` - 成功提示
- `failure` - 失败提示
- `none` - 无声

### 自定义图标

可以通过 `icon` 参数自定义推送图标：
```python
bark_notifier.send(
    title="测试",
    content="这是一条测试消息",
    icon="https://example.com/icon.png"
)
```

### 推送链接

可以添加链接，点击后打开指定 URL：
```python
bark_notifier.send(
    title="查看日志",
    content="点击查看详情",
    url="http://your-server.com/logs"
)
```

## API 参考

### BarkNotifier 类

```python
class BarkNotifier:
    def send(title, content, level, sound, volume, group, icon):
        """发送任意 Bark 通知"""
    
    def notify_error(error_title, error_message, context):
        """发送错误通知"""
    
    def notify_trade(trade_type, symbol, details):
        """发送交易通知"""
    
    def notify_signal(symbol, signal_type, score, details):
        """发送信号通知"""
    
    def notify_status(status_type, title, content, is_important):
        """发送状态通知"""
    
    def notify_daily_heartbeat(summary):
        """发送每日总结"""
```

### 通知级别

- `LEVEL_CRITICAL` - 强提醒（破防模式）
- `LEVEL_ACTIVE` - 主动提醒
- `LEVEL_PASSIVE` - 被动提醒
- `LEVEL_NONE` - 不推送

## 最佳实践

1. **初次使用**：先开启所有通知，观察推送频率
2. **调整优化**：根据实际体验调整冷却时间
3. **夜间模式**：可以在夜间关闭非关键通知
4. **定期检查**：查看错误日志，修复频繁出现的错误
5. **备份配置**：保存多份配置文件，方便切换

## 安全提示

- **保护设备密钥**：不要公开分享您的 `device_key`
- **API 限流**：Bark 有 API 调用限制，避免过度推送
- **错误处理**：系统会自动处理推送失败，不影响主程序运行

---

**更新日期**：2026-04-14
**版本**：v1.0.0
