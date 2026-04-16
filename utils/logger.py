import logging
import sys
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 延迟导入 BarkNotifier，避免循环依赖
BarkNotifier = None


def setup_logging(config: dict, bark_notifier=None) -> None:
    """
    设置日志系统
    
    Args:
        config: 配置字典
        bark_notifier: Bark 通知器实例（可选）
    """
    logging_cfg = config.get("logging", {})
    level_name = str(logging_cfg.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    file_path = Path(logging_cfg.get("file_path", "logs/bot.log"))
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    error_log_path = file_path.parent / "error.log"
    detailed_log_path = file_path.parent / "detailed.log"

    standard_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(module)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(standard_formatter)
    stream_handler.setLevel(level)

    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=5_000_000,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(standard_formatter)
    file_handler.setLevel(level)
    
    detailed_handler = RotatingFileHandler(
        detailed_log_path,
        maxBytes=10_000_000,
        backupCount=15,
        encoding="utf-8",
    )
    detailed_handler.setFormatter(detailed_formatter)
    detailed_handler.setLevel(logging.DEBUG)
    
    # 创建自定义的 Error Handler，带 Bark 通知
    error_handler = RotatingFileHandler(
        error_log_path,
        maxBytes=5_000_000,
        backupCount=10,
        encoding="utf-8",
    )
    error_handler.setFormatter(detailed_formatter)
    error_handler.setLevel(logging.ERROR)
    
    # 如果提供了 Bark 通知器，添加 Bark 通知功能
    if bark_notifier:
        error_handler = BarkNotificationHandler(
            error_handler,
            bark_notifier,
            config
        )

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(stream_handler)
    root.addHandler(file_handler)
    root.addHandler(detailed_handler)
    root.addHandler(error_handler)
    
    logging.captureWarnings(True)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_exception(logger: logging.Logger, message: str, exc: Exception) -> None:
    """记录异常详情，包括堆栈跟踪"""
    logger.error(f"{message} | exception_type={type(exc).__name__} | error={str(exc)}")
    logger.debug(f"Stack trace:\n{traceback.format_exc()}")


def log_system_status(logger: logging.Logger, status_type: str, details: dict) -> None:
    """记录系统状态信息"""
    timestamp = datetime.now().isoformat()
    logger.info(f"[SYSTEM_STATUS] {status_type} | timestamp={timestamp} | {format_dict(details)}")


def format_dict(d: dict, prefix: str = "") -> str:
    """格式化字典为日志字符串"""
    items = []
    for key, value in d.items():
        if isinstance(value, dict):
            items.append(format_dict(value, f"{prefix}{key}."))
        else:
            items.append(f"{prefix}{key}={value}")
    return " | ".join(items)


class DiagnosticContext:
    """上下文管理器，用于记录代码块的执行情况和性能"""
    
    def __init__(self, logger: logging.Logger, operation: str, extra_data: dict = None):
        self.logger = logger
        self.operation = operation
        self.extra_data = extra_data or {}
        self.start_time = None
        
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"[DIAGNOSTIC] Starting operation: {self.operation} | {format_dict(self.extra_data)}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        if exc_type is not None:
            self.logger.error(
                f"[DIAGNOSTIC] Operation failed: {self.operation} | "
                f"duration={duration:.3f}s | exception={type(exc_val).__name__}: {str(exc_val)}"
            )
            self.logger.debug(f"Stack trace:\n{traceback.format_exc()}")
        else:
            self.logger.debug(
                f"[DIAGNOSTIC] Operation completed: {self.operation} | duration={duration:.3f}s"
            )
        return False


class BarkNotificationHandler(logging.Handler):
    """
    包装普通的 FileHandler，在记录 ERROR 级别日志时发送 Bark 通知
    """
    
    def __init__(self, handler: logging.Handler, bark_notifier, config: dict):
        # 必须调用父类的 __init__，并继承被包装 handler 的日志级别！
        super().__init__(level=handler.level)
        
        self.wrapped_handler = handler
        self.bark_notifier = bark_notifier
        self.config = config
        self.logger = bark_notifier.logger  # 使用 bark_notifier 的 logger
        
        # 错误通知限制
        self.error_cooldown_seconds = int(
            config.get("bark", {}).get("error_cooldown_minutes", 10)
        ) * 60
        self._last_error_time = None
        self._error_count = 0
        
        # 将被包装 handler 的 formatter 也继承过来
        if handler.formatter:
            self.setFormatter(handler.formatter)
    
    def close(self):
        super().close()
        self.wrapped_handler.close()
    
    def emit(self, record):
        import time
        
        # 首先：调用原 handler 的 emit，确保日志一定能写入文件
        try:
            self.wrapped_handler.emit(record)
        except Exception:
            self.handleError(record)
        
        # 然后：执行 Bark 推送逻辑
        try:
            # 如果是 ERROR 级别，尝试发送 Bark 通知
            if record.levelno >= logging.ERROR and self.bark_notifier:
                # 格式化日志内容用于推送
                msg = self.format(record)
                
                # 简单的冷却时间检查 (防止 ERROR 刷屏导致 Bark API 熔断)
                current_time = time.time()
                if self._last_error_time is None or (current_time - self._last_error_time) >= self.error_cooldown_seconds:
                    self._last_error_time = current_time
                    
                    # 触发推送
                    if self.bark_notifier and getattr(self.bark_notifier, "notify_on_error", True):
                        self.bark_notifier.notify_error(
                            error_title=f"{record.name} - {record.levelname}",
                            error_message=record.getMessage(),
                            context={
                                "文件": record.filename,
                                "行号": record.lineno,
                                "详情": msg,
                            },
                        )
        except Exception:
            # 如果推送失败，交给 logging 模块的安全机制处理，不要阻塞主线程
            self.handleError(record)
    
    def _send_bark_notification(self, record):
        """发送 Bark 错误通知"""
        now = datetime.now()
        
        # 检查冷却时间
        if self._last_error_time:
            elapsed = (now - self._last_error_time).total_seconds()
            if elapsed < self.error_cooldown_seconds:
                self._error_count += 1
                return

        # 提取错误信息
        error_title = f"{record.name} - {record.funcName}"
        error_message = record.getMessage()
        
        # 添加上下文信息
        context = {
            "模块": record.name,
            "函数": record.funcName,
            "文件": record.pathname,
            "行号": record.lineno,
            "时间": now.strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        # 如果有异常信息，添加到 context
        if record.exc_info:
            context["异常"] = f"{record.exc_info[0].__name__}: {record.exc_info[1]}"
        
        # 发送通知
        self.bark_notifier.notify_error(
            error_title=error_title,
            error_message=error_message,
            context=context
        )
        
        # 更新最后错误时间
        self._last_error_time = now
        if self._error_count > 0:
            self.bark_notifier.logger.info(
                "Skipped %d error notifications during cooldown",
                self._error_count
            )
            self._error_count = 0
