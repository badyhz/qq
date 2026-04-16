"""
Bark 消息推送工具
负责将系统关键事件推送到用户 iOS 设备
"""

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Optional


class BarkNotifier:
    """Bark 消息推送器"""
    
    # 配置常量
    BASE_URL = "https://api.day.app"
    DEVICE_KEY = "qQH2uNcLvpFuqfHqykmMCD"  # 用户设备密钥
    
    # 通知级别
    LEVEL_CRITICAL = "critical"  # 强提醒（破防模式）
    LEVEL_ACTIVE = "active"      # 主动提醒
    LEVEL_PASSIVE = "passive"    # 被动提醒
    LEVEL_NONE = "none"          # 不提醒
    
    def __init__(self, config: dict, logger):
        """
        初始化 Bark 通知器
        
        Args:
            config: 配置字典，可从 config.yaml 的 bark 节点读取
            logger: 日志记录器
        """
        self.config = config
        self.logger = logger
        self.device_key = config.get("bark", {}).get("device_key", self.DEVICE_KEY)
        self.enabled = config.get("bark", {}).get("enabled", True)
        
        # 通知开关
        self.notify_on_error = config.get("bark", {}).get("notify_on_error", True)
        self.notify_on_trade = config.get("bark", {}).get("notify_on_trade", True)
        self.notify_on_signal = config.get("bark", {}).get("notify_on_signal", True)
        self.notify_on_status = config.get("bark", {}).get("notify_on_status", False)
        
        # 错误通知限制（避免频繁推送）
        self.error_cooldown_minutes = int(config.get("bark", {}).get("error_cooldown_minutes", 10))
        self._last_error_notify = None
        self._error_count = 0
        
        # 交易通知限制
        self.trade_cooldown_minutes = int(config.get("bark", {}).get("trade_cooldown_minutes", 5))
        self._last_trade_notify = None
        
        # 状态推送间隔（小时）
        self.status_interval_hours = int(config.get("bark", {}).get("status_interval_hours", 6))
        self._last_status_notify = None
    
    def _build_url(self, title: str, content: str, params: dict = None) -> str:
        """
        构建 Bark API URL
        
        Args:
            title: 推送标题
            content: 推送内容
            params: 额外参数（如 level, sound, volume 等）
        
        Returns:
            完整的 API URL
        """
        # URL 编码标题和内容
        encoded_title = urllib.parse.quote(title, safe="")
        encoded_content = urllib.parse.quote(content, safe="")
        
        # 构建基础 URL
        url = f"{self.BASE_URL}/{self.device_key}/{encoded_title}/{encoded_content}"
        
        # 添加额外参数
        if params:
            query_params = "&".join(f"{k}={v}" for k, v in params.items())
            url += f"?{query_params}"
        
        return url
    
    def _send_request(self, url: str) -> bool:
        """
        发送 HTTP GET 请求到 Bark API
        
        Args:
            url: Bark API URL
        
        Returns:
            是否发送成功
        """
        try:
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode())
                if result.get("code") == 200:
                    self.logger.debug("Bark notification sent | title=%s", url.split('/')[4])
                    return True
                else:
                    self.logger.error("Bark API returned error | code=%s | message=%s", 
                                    result.get("code"), result.get("message"))
                    return False
        except Exception as e:
            self.logger.error("Failed to send Bark notification | error=%s", str(e))
            return False
    
    def _should_notify(self, notify_type: str, cooldown_minutes: int, 
                      last_notify_time: Optional[datetime]) -> bool:
        """
        检查是否应该发送通知（避免频繁推送）
        
        Args:
            notify_type: 通知类型
            cooldown_minutes: 冷却时间（分钟）
            last_notify_time: 上次通知时间
        
        Returns:
            是否应该发送
        """
        if not self.enabled:
            return False
        
        if last_notify_time is None:
            return True
        
        now = datetime.now(timezone.utc)
        cooldown = (now - last_notify_time).total_seconds() / 60
        
        if cooldown < cooldown_minutes:
            self.logger.debug(
                "Bark notification skipped (cooldown) | type=%s | cooldown_remaining=%.1fmin",
                notify_type, cooldown_minutes - cooldown
            )
            return False
        
        return True
    
    def send(self, title: str, content: str, level: str = LEVEL_PASSIVE, 
             sound: Optional[str] = None, volume: Optional[int] = None,
             group: Optional[str] = None, icon: Optional[str] = None) -> bool:
        """
        发送 Bark 通知
        
        Args:
            title: 标题
            content: 内容
            level: 通知级别（critical/active/passive/none）
            sound: 提示音（如 alarm, bell, success 等）
            volume: 音量（0-10）
            group: 消息分组
            icon: 自定义图标 URL
        
        Returns:
            是否发送成功
        """
        self.logger.info("Bark send called | title=%s | level=%s", title, level)
        
        if not self.enabled:
            self.logger.debug("Bark notifier is disabled, skipping notification")
            return False
        
        if level == self.LEVEL_NONE:
            return False
        
        # 构建参数
        params = {}
        if level:
            params["level"] = level
        if sound:
            params["sound"] = sound
        if volume:
            params["volume"] = str(volume)
        if group:
            params["group"] = group
        if icon:
            params["icon"] = icon
        
        url = self._build_url(title, content, params)
        self.logger.info("Bark sending | url=%s", url)
        result = self._send_request(url)
        self.logger.info("Bark send result | success=%s", result)
        return result
    
    def notify_error(self, error_title: str, error_message: str, 
                    context: Optional[dict] = None) -> bool:
        """
        发送错误通知（强提醒）
        
        Args:
            error_title: 错误标题
            error_message: 错误详情
            context: 额外上下文信息
        
        Returns:
            是否发送成功
        """
        if not self.notify_on_error:
            return False
        
        # 检查冷却时间
        if not self._should_notify("error", self.error_cooldown_minutes, 
                                   self._last_error_notify):
            self._error_count += 1
            return False
        
        # 构建通知内容
        title = f"⚠️ 系统错误：{error_title}"
        content = error_message
        if context:
            content += "\n\n" + "\n".join(f"{k}: {v}" for k, v in context.items())
        
        # 发送强提醒
        success = self.send(
            title=title,
            content=content,
            level=self.LEVEL_CRITICAL,
            sound="alarm",
            volume=10,
            group="errors"
        )
        
        if success:
            self._last_error_notify = datetime.now(timezone.utc)
            self.logger.info(
                "Error notification sent | title=%s | error_count=%s",
                error_title, self._error_count
            )
        
        return success
    
    def notify_trade(self, trade_type: str, symbol: str, details: dict) -> bool:
        """
        发送交易通知（强提醒）
        
        Args:
            trade_type: 交易类型（开仓/平仓/止盈/止损等）
            symbol: 交易对
            details: 交易详情
        
        Returns:
            是否发送成功
        """
        if not self.notify_on_trade:
            return False
        
        # 检查冷却时间
        if not self._should_notify("trade", self.trade_cooldown_minutes,
                                   self._last_trade_notify):
            return False
        
        # 构建通知内容
        emoji_map = {
            "open": "🎯",
            "close": "💰",
            "tp": "✅",
            "sl": "❌",
            "timeout": "⏰",
            "breakeven": "🛡️"
        }
        emoji = emoji_map.get(trade_type.lower(), "📊")
        
        title = f"{emoji} {trade_type}: {symbol}"
        content = "\n".join(f"{k}: {v}" for k, v in details.items())
        
        # 发送强提醒
        success = self.send(
            title=title,
            content=content,
            level=self.LEVEL_CRITICAL,
            sound="alarm",
            volume=10,
            group="trades"
        )
        
        if success:
            self._last_trade_notify = datetime.now(timezone.utc)
            self.logger.info("Trade notification sent | type=%s | symbol=%s", trade_type, symbol)
        
        return success
    
    def notify_signal(self, symbol: str, signal_type: str, score: int, 
                     details: dict) -> bool:
        """
        发送信号通知（强提醒）
        
        Args:
            symbol: 交易对
            signal_type: 信号类型
            score: 信号评分
            details: 信号详情
        
        Returns:
            是否发送成功
        """
        if not self.notify_on_signal:
            return False
        
        title = f"🎯 狙击指令：{symbol}"
        content = f"信号类型：{signal_type}\n评分：{score}\n\n"
        content += "\n".join(f"{k}: {v}" for k, v in details.items())
        
        # 发送强提醒
        success = self.send(
            title=title,
            content=content,
            level=self.LEVEL_CRITICAL,
            sound="alarm",
            volume=10,
            group="signals"
        )
        
        if success:
            self.logger.info("Signal notification sent | symbol=%s | score=%s", symbol, score)
        
        return success
    
    def notify_status(self, status_type: str, title: str, content: str,
                     is_important: bool = False) -> bool:
        """
        发送状态通知（常规提醒）
        
        Args:
            status_type: 状态类型
            title: 标题
            content: 内容
            is_important: 是否重要（决定是否使用强提醒）
        
        Returns:
            是否发送成功
        """
        if not self.notify_on_status:
            return False
        
        # 检查冷却时间（状态通知冷却时间更长）
        cooldown = 60 if is_important else self.status_interval_hours * 60
        if not self._should_notify("status", cooldown, self._last_status_notify):
            return False
        
        # 发送通知
        level = self.LEVEL_CRITICAL if is_important else self.LEVEL_PASSIVE
        sound = "alarm" if is_important else None
        
        success = self.send(
            title=title,
            content=content,
            level=level,
            sound=sound,
            volume=10 if is_important else None,
            group="status"
        )
        
        if success:
            self._last_status_notify = datetime.now(timezone.utc)
            self.logger.info("Status notification sent | type=%s", status_type)
        
        return success
    
    def notify_daily_heartbeat(self, summary: dict) -> bool:
        """
        发送每日系统心跳
        
        Args:
            summary: 每日总结数据
        
        Returns:
            是否发送成功
        """
        title = "🌅 系统晨间报告"
        content = (
            f"日期：{summary.get('date', 'N/A')}\n"
            f"总交易数：{summary.get('total_trades', 0)}\n"
            f"胜率：{summary.get('win_rate', 0):.1f}%\n"
            f"总盈亏：{summary.get('total_pnl', 0):.2f} USDT\n"
            f"当前余额：{summary.get('balance', 0):.2f} USDT"
        )
        
        return self.send(
            title=title,
            content=content,
            level=self.LEVEL_PASSIVE,
            sound="success",
            group="daily"
        )
