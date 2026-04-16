import copy
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import yaml

from core.data_feed import DataFeed
from core.execution import ExecutionEngine
from core.exchange import ExchangeClient
from core.order_manager import OrderManager
from core.risk_manager import RiskManager
from core.signal_engine import SignalEngine
from core.ticker_scanner import TickerScanner
from core.trade_logger import TradeLogger
from utils.bark_notifier import BarkNotifier
from utils.logger import DiagnosticContext, get_logger, log_system_status, setup_logging


DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.yaml")


def format_price(value: float) -> str:
    price = float(value)
    abs_price = abs(price)
    if abs_price >= 1000:
        decimals = 2
    elif abs_price >= 1:
        decimals = 4
    elif abs_price >= 0.01:
        decimals = 5
    else:
        decimals = 6
    return f"{price:.{decimals}f}"


def normalize_config(config: dict) -> dict:
    normalized = dict(config)
    radar_cfg = dict(normalized.get("radar", {}))
    radar_enabled = bool(radar_cfg.get("enabled", False))
    experiment_cfg = dict(normalized.get("experiment", {}))
    raw_symbols = normalized.get("symbols")
    if raw_symbols is None and not radar_enabled:
        raw_symbols = [normalized.get("symbol", "BTCUSDT")]
    elif raw_symbols is None:
        raw_symbols = []

    symbols = []
    seen = set()
    for symbol in raw_symbols:
        cleaned = str(symbol).strip().upper()
        if not cleaned or cleaned in seen:
            continue
        symbols.append(cleaned)
        seen.add(cleaned)

    if not symbols and not radar_enabled:
        symbols = ["BTCUSDT"]

    normalized["symbols"] = symbols
    normalized["symbol"] = symbols[0] if symbols else normalized.get("symbol", "BTCUSDT")

    portfolio = dict(normalized.get("portfolio", {}))
    default_max_positions = 3 if radar_enabled and not symbols else (1 if len(symbols) == 1 else min(3, len(symbols)))
    portfolio.setdefault("max_open_positions", default_max_positions)
    normalized["portfolio"] = portfolio
    normalized["radar"] = radar_cfg

    strategy = dict(normalized.get("strategy", {}))
    strategy_profiles = dict(normalized.get("strategy_profiles", {}))
    active_strategy_profile = str(
        os.environ.get(
            "QQ_STRATEGY_PROFILE",
            experiment_cfg.get("active_strategy_profile", strategy.get("profile_name", "default")),
        )
    ).strip()
    if active_strategy_profile and active_strategy_profile in strategy_profiles:
        strategy.update(strategy_profiles[active_strategy_profile])
    strategy["profile_name"] = active_strategy_profile or strategy.get("profile_name", "default")
    normalized["strategy"] = strategy
    normalized["strategy_profile"] = strategy["profile_name"]

    experiment_cfg.setdefault("active_strategy_profile", normalized["strategy_profile"])
    experiment_cfg.setdefault("baseline_strategy_profile", "baseline")
    experiment_cfg.setdefault("compare_profiles", ["baseline", normalized["strategy_profile"]])
    normalized["experiment"] = experiment_cfg

    paths = dict(normalized.get("paths", {}))
    trades_csv_template = paths.get("trades_csv_template")
    if trades_csv_template and "{profile}" in str(trades_csv_template):
        paths["trades_csv"] = str(trades_csv_template).format(profile=normalized["strategy_profile"])
    normalized["paths"] = paths
    return normalized


def load_config() -> dict:
    config_path = Path(os.environ.get("QQ_CONFIG_PATH", DEFAULT_CONFIG_PATH))
    with DiagnosticContext(get_logger("init"), "load_config", {"config_path": str(config_path)}):
        with config_path.open("r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle) or {}
        config = normalize_config(config)
        config["_config_path"] = str(config_path)
        return config


def build_runtime(config: dict) -> dict:
    runtime = dict(config.get("runtime", {}))
    env_max_loops = os.environ.get("QQ_MAX_LOOPS")
    env_loop_interval = os.environ.get("QQ_LOOP_INTERVAL_SECONDS")
    env_heartbeat_interval = os.environ.get("QQ_HEARTBEAT_INTERVAL_SECONDS")
    if env_max_loops is not None:
        runtime["max_loops"] = int(env_max_loops)
    if env_loop_interval is not None:
        runtime["loop_interval_seconds"] = float(env_loop_interval)
    if env_heartbeat_interval is not None:
        runtime["heartbeat_interval_seconds"] = float(env_heartbeat_interval)
    runtime.setdefault("loop_interval_seconds", 1.0)
    runtime.setdefault("heartbeat_interval_seconds", 30)
    runtime.setdefault("max_loops", 0)
    return runtime


def build_symbol_config(config: dict, symbol: str) -> dict:
    symbol_config = copy.deepcopy(config)
    symbol_config["symbol"] = symbol
    return symbol_config


def warmup_signal_engines(signal_engines: dict, candles_by_symbol: dict) -> None:
    for symbol, candles in candles_by_symbol.items():
        if symbol in signal_engines and candles:
            signal_engines[symbol].seed_history(candles)


class TradingApplication:
    def __init__(self, config: dict):
        self.config = config
        self.runtime = build_runtime(config)
        self.seed_symbols = list(config.get("symbols", []))
        self.symbols = []
        self.radar_enabled = bool(config.get("radar", {}).get("enabled", False))
        self.max_open_positions = int(config.get("portfolio", {}).get("max_open_positions", 1))
        self.started_at = time.time()
        self.guard_timestamps = {}

        startup_time = datetime.now(timezone.utc).isoformat()
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        bark_notifier = BarkNotifier(config, get_logger("bark"))
        setup_logging(config, bark_notifier)
        self.logger = get_logger("app")

        self.logger.info("=" * 80)
        self.logger.info("TRADING BOT STARTUP INITIALIZATION")
        self.logger.info("=" * 80)
        self.logger.info("Startup timestamp: %s", startup_time)
        self.logger.info("Python version: %s", python_version)
        self.logger.info("Config file: %s", config.get("_config_path", "unknown"))
        self.logger.info("Mode: %s | Data mode: %s", config.get("mode"), config.get("data_mode"))
        self.logger.info(
            "Symbols: %s | Timeframe: %s | Radar enabled=%s",
            ", ".join(self.seed_symbols) if self.seed_symbols else "DYNAMIC",
            config.get("timeframe"),
            self.radar_enabled,
        )

        log_system_status(
            self.logger,
            "INIT_START",
            {
                "mode": config.get("mode"),
                "data_mode": config.get("data_mode"),
                "symbols": ",".join(self.seed_symbols) if self.seed_symbols else "DYNAMIC",
                "timeframe": config.get("timeframe"),
                "python_version": python_version,
                "startup_time": startup_time,
            },
        )

        self.bark_notifier = bark_notifier
        self.trade_logger = TradeLogger(config)
        self.risk_manager = RiskManager(config, self.logger)
        self.data_feed = DataFeed(config, self.logger)
        self.ticker_scanner = TickerScanner(config, self.logger) if self.radar_enabled else None

        self.symbol_configs = {}
        self.signal_engines = {}
        self.order_managers = {}
        self.exchanges = {}
        self.executions = {}

        with DiagnosticContext(self.logger, "init_components", {"symbols": len(self.seed_symbols)}):
            self.logger.info("Trade logger initialized | file=%s", self.trade_logger.file_path)
            self.logger.info(
                "Risk manager initialized | starting_balance=%s | risk_per_trade=%s%% | max_open_positions=%s",
                config.get("risk", {}).get("starting_balance_usdt"),
                config.get("risk", {}).get("risk_per_trade", 0) * 100,
                self.max_open_positions,
            )

            self.logger.info("Data feed initialized | active_symbols=%s", ",".join(self.data_feed.get_active_symbols()) or "NONE")
            if self.ticker_scanner:
                self.logger.info("Ticker scanner initialized | update_interval=%ss", self.ticker_scanner.update_interval)

        initial_target_symbols = self._get_initial_target_symbols()
        self._sync_symbol_pool(initial_target_symbols, reason="startup")

        log_system_status(
            self.logger,
            "INIT_COMPLETE",
            {
                "symbols": ",".join(self.symbols) if self.symbols else "NONE",
                "exchange_enabled_symbols": ",".join(
                    symbol for symbol in self.symbols if self.exchanges[symbol].is_enabled()
                ),
                "initialization_status": "success",
            },
        )
        self.logger.info("=" * 80)
        self._send_startup_notification(startup_time, python_version)

    def _active_position_symbols(self) -> list:
        return [symbol for symbol, manager in self.order_managers.items() if manager.has_position()]

    def _get_initial_target_symbols(self) -> set:
        if self.radar_enabled and self.ticker_scanner:
            initial_hot = self.ticker_scanner.scan(force=True)
            if initial_hot:
                return set(initial_hot)
        return set(self.seed_symbols)

    def _create_symbol_runtime(self, symbol: str) -> None:
        if symbol in self.signal_engines:
            return

        symbol_config = build_symbol_config(self.config, symbol)
        self.symbol_configs[symbol] = symbol_config
        self.signal_engines[symbol] = SignalEngine(symbol_config, self.logger)
        self.order_managers[symbol] = OrderManager(symbol_config)
        self.exchanges[symbol] = ExchangeClient(symbol_config, self.logger)
        self.executions[symbol] = ExecutionEngine(
            config=symbol_config,
            order_manager=self.order_managers[symbol],
            exchange=self.exchanges[symbol],
            logger=self.logger,
        )
        self.guard_timestamps[symbol] = 0.0
        self.logger.info(
            "Per-symbol components initialized | symbol=%s | exchange_enabled=%s",
            symbol,
            self.exchanges[symbol].is_enabled(),
        )
        self._restore_live_position_if_any(symbol)

    def _restore_live_position_if_any(self, symbol: str) -> None:
        exchange = self.exchanges[symbol]
        if not exchange.is_enabled():
            return

        with DiagnosticContext(self.logger, "exchange_health_check", {"symbol": symbol}):
            self.logger.info("Performing exchange health check | symbol=%s", symbol)
            exchange.ping()
            live_snapshot = exchange.fetch_position_snapshot()
            if live_snapshot:
                live_snapshot.update(exchange.fetch_protection_snapshot())
                self.order_managers[symbol].restore_live_position(live_snapshot)
                self.logger.warning(
                    "LIVE POSITION RESTORED FROM EXCHANGE | symbol=%s | side=%s | qty=%s",
                    live_snapshot.get("symbol"),
                    live_snapshot.get("side"),
                    live_snapshot.get("quantity"),
                )

    def _destroy_symbol_runtime(self, symbol: str) -> None:
        if symbol in self.order_managers and self.order_managers[symbol].has_position():
            return
        self.signal_engines.pop(symbol, None)
        self.order_managers.pop(symbol, None)
        self.exchanges.pop(symbol, None)
        self.executions.pop(symbol, None)
        self.symbol_configs.pop(symbol, None)
        self.guard_timestamps.pop(symbol, None)
        self.logger.info("Per-symbol components destroyed | symbol=%s", symbol)

    def _sync_symbol_pool(self, target_symbols: set, reason: str) -> None:
        normalized_targets = {str(symbol).strip().upper() for symbol in target_symbols if str(symbol).strip()}
        locked_symbols = set(self._active_position_symbols())
        protected_targets = normalized_targets | locked_symbols
        current_symbols = set(self.signal_engines.keys())
        added_symbols = sorted(protected_targets - current_symbols)
        removable_symbols = sorted(current_symbols - protected_targets)

        bootstrap_candles = self.data_feed.update_subscriptions(protected_targets)
        missing_bootstrap_symbols = [symbol for symbol in added_symbols if not bootstrap_candles.get(symbol)]
        if missing_bootstrap_symbols:
            extra_bootstrap = self.data_feed.bootstrap_symbols(missing_bootstrap_symbols)
            for symbol, candles in extra_bootstrap.items():
                bootstrap_candles[symbol] = candles

        for symbol in added_symbols:
            self._create_symbol_runtime(symbol)

        warmup_signal_engines(self.signal_engines, bootstrap_candles)
        for symbol in added_symbols:
            self.logger.info(
                "Symbol activated | reason=%s | symbol=%s | warmup_candles=%s",
                reason,
                symbol,
                len(bootstrap_candles.get(symbol, [])),
            )

        for symbol in removable_symbols:
            if symbol in locked_symbols:
                self.logger.info("Symbol kept due to open position lock | symbol=%s", symbol)
                continue
            self._destroy_symbol_runtime(symbol)

        self.symbols = list(self.signal_engines.keys())
        self.logger.info(
            "Symbol pool synced | reason=%s | active=%s | locked=%s",
            reason,
            ",".join(self.symbols) if self.symbols else "NONE",
            ",".join(sorted(locked_symbols)) if locked_symbols else "NONE",
        )

    def _can_open_global_position(self, symbol: str) -> tuple:
        active_symbols = self._active_position_symbols()
        if self.order_managers[symbol].has_position():
            return False, "symbol_position_exists"
        if len(active_symbols) >= self.max_open_positions:
            return False, "global_position_limit"
        return True, "ok"

    def _send_startup_notification(self, startup_time: str, python_version: str) -> bool:
        if not self.bark_notifier:
            return False

        mode = self.config.get("mode", "dry-run")
        timeframe = self.config.get("timeframe", "5m")
        symbol_text = ", ".join(self.symbols[:6]) if self.symbols else "DYNAMIC_RADAR"
        if len(self.symbols) > 6:
            symbol_text += f" ... (+{len(self.symbols) - 6})"

        title = "🤖 量化系统启动"
        content = (
            f"模式：{mode}\n"
            f"交易对：{symbol_text}\n"
            f"周期：{timeframe}\n"
            f"Python: {python_version}\n"
            f"启动时间：{startup_time}"
        )

        return self.bark_notifier.send(
            title=title,
            content=content,
            level=self.bark_notifier.LEVEL_ACTIVE,
            sound="success",
            group="system",
        )

    def _send_trade_closed_notification(self, trade: dict) -> bool:
        if not self.bark_notifier or not self.bark_notifier.notify_on_trade:
            return False

        exit_reason = str(trade.get("exit_reason", "close")).lower()
        type_map = {
            "take_profit": "tp",
            "stop_loss": "sl",
            "timeout": "timeout",
            "breakeven": "breakeven",
            "opposite_signal": "close",
            "risk_management": "close",
        }
        trade_type = type_map.get(exit_reason, "close")

        pnl = trade.get("pnl", 0)
        pnl_symbol = "✅" if pnl > 0 else "❌"
        details = {
            f"{pnl_symbol} 盈亏": f"{pnl:.2f} USDT",
            "交易对": trade.get("symbol", "UNKNOWN"),
            "退出原因": exit_reason,
            "评分": trade.get("score", "N/A"),
            "持续时间": f"{trade.get('duration_sec', 0):.0f}秒",
        }

        return self.bark_notifier.notify_trade(
            trade_type=trade_type,
            symbol=trade.get("symbol", "UNKNOWN"),
            details=details,
        )

    def _send_signal_notification(self, symbol: str, signal: dict) -> bool:
        if not self.bark_notifier or not self.bark_notifier.notify_on_signal:
            return False

        signal_meta = signal.get("meta", {})
        signal_details = {
            "评分": signal.get("score", 0),
            "Z 分数": f"{signal_meta.get('zscore', 0):.4f}",
            "入场": format_price(signal.get("entry", 0)),
            "止损": format_price(signal.get("stop", 0)),
            "目标": format_price(signal.get("tp", 0)),
            "止损幅度": f"{signal_meta.get('stop_pct', 0.0) * 100:.2f}%",
            "盈亏比": f"{signal_meta.get('reward_risk_ratio', 0.0):.2f}",
        }
        return self.bark_notifier.notify_signal(
            symbol=symbol,
            signal_type="做空信号",
            score=signal.get("score", 0),
            details=signal_details,
        )

    def run(self) -> None:
        heartbeat_interval = self.runtime["heartbeat_interval_seconds"]
        loop_interval = self.runtime["loop_interval_seconds"]
        max_loops = self.runtime["max_loops"]
        loop_count = 0
        last_heartbeat = time.time()
        loop_times = []
        error_count = 0

        self.logger.info(
            "Runtime configuration | loop_interval=%ss | heartbeat_interval=%ss | max_loops=%s",
            loop_interval,
            heartbeat_interval,
            max_loops,
        )

        while True:
            loop_started = time.time()
            loop_iteration = loop_count + 1

            try:
                with DiagnosticContext(self.logger, f"loop_{loop_iteration}", {"iteration": loop_iteration}):
                    if self.radar_enabled and self.ticker_scanner and self.ticker_scanner.should_scan():
                        hot_symbols = self.ticker_scanner.scan(force=False)
                        self._sync_symbol_pool(set(hot_symbols), reason="radar_update")

                    market = self.data_feed.get_latest()
                    loop_count += 1
                    if max_loops and loop_count >= max_loops and not market:
                        self.logger.info("MAX LOOPS REACHED | loops_completed=%s | exiting gracefully", loop_count)
                        break
                    if not market:
                        self.logger.debug("No market data available, waiting... | active_symbols=%s", ",".join(self.symbols) or "NONE")
                        time.sleep(loop_interval)
                        continue

                    symbol = market["symbol"]
                    if symbol not in self.signal_engines:
                        self.logger.warning("Received market data for unmanaged symbol | symbol=%s", symbol)
                        continue

                    order_manager = self.order_managers[symbol]
                    signal_engine = self.signal_engines[symbol]
                    execution = self.executions[symbol]
                    exchange = self.exchanges[symbol]

                    closed_trade = order_manager.update_market(market)
                    if closed_trade:
                        with DiagnosticContext(
                            self.logger,
                            "trade_closed",
                            {"trade_id": closed_trade.get("trade_id"), "symbol": symbol},
                        ):
                            self.trade_logger.log_trade(closed_trade)
                            self.risk_manager.on_trade_closed(closed_trade)
                            signal_engine.on_trade_closed(closed_trade)
                            pnl = closed_trade.get("pnl", 0)
                            pnl_status = "WIN" if pnl > 0 else "LOSS"
                            self.logger.info(
                                "TRADE CLOSED | symbol=%s | id=%s | reason=%s | pnl=%.4f USDT | status=%s",
                                symbol,
                                closed_trade["trade_id"],
                                closed_trade["exit_reason"],
                                pnl,
                                pnl_status,
                            )
                            self._send_trade_closed_notification(closed_trade)
                            log_system_status(
                                self.logger,
                                "TRADE_CLOSED",
                                {
                                    "trade_id": closed_trade.get("trade_id"),
                                    "symbol": symbol,
                                    "exit_reason": closed_trade.get("exit_reason"),
                                    "pnl": pnl,
                                    "pnl_status": pnl_status,
                                    "score": closed_trade.get("score"),
                                },
                            )

                    if exchange.is_enabled() and order_manager.has_position():
                        guard_interval = self.config.get("execution", {}).get("guard_check_interval_seconds", 5)
                        now_ts = time.time()
                        last_guard = self.guard_timestamps.get(symbol, 0.0)
                        if now_ts - last_guard >= guard_interval:
                            execution.ensure_live_protection()
                            self.guard_timestamps[symbol] = now_ts

                    if market.get("closed"):
                        signal = signal_engine.on_candle(market, has_position=order_manager.has_position())

                        if signal["action"] == "SHORT":
                            signal_meta = signal.get("meta", {})
                            self.logger.debug(
                                "Trading signal detected | symbol=%s | action=%s | score=%s | zscore=%.4f",
                                symbol,
                                signal["action"],
                                signal.get("score"),
                                signal_meta.get("zscore", 0.0),
                            )
                            self._send_signal_notification(symbol, signal)

                            allowed, reason = self.risk_manager.can_open_new_trade(symbol, market["timestamp"])
                            global_allowed, global_reason = self._can_open_global_position(symbol)

                            if not allowed:
                                self.logger.info(
                                    "SIGNAL REJECTED by risk manager | symbol=%s | reason=%s | score=%s",
                                    symbol,
                                    reason,
                                    signal.get("score"),
                                )
                            elif not global_allowed:
                                self.logger.info(
                                    "SIGNAL REJECTED by global position rule | symbol=%s | reason=%s | active=%s",
                                    symbol,
                                    global_reason,
                                    ",".join(self._active_position_symbols()),
                                )
                            else:
                                with DiagnosticContext(
                                    self.logger,
                                    "open_position",
                                    {
                                        "symbol": symbol,
                                        "signal_score": signal.get("score"),
                                        "signal_zscore": signal_meta.get("zscore", 0.0),
                                    },
                                ):
                                    position_plan = self.risk_manager.calculate_position(
                                        signal,
                                        symbol=symbol,
                                        open_positions=len(self._active_position_symbols()),
                                    )
                                    execution_result = execution.open_short(position_plan, signal, market)
                                    if execution_result.get("accepted"):
                                        order_manager.open_position(execution_result, signal, market)
                                        signal_engine.on_position_opened()
                                        self.logger.info(
                                            "POSITION OPENED | symbol=%s | mode=%s | qty=%.6f | entry=%s | stop=%s | tp=%s | rr=%.2f | est_loss=%.4f | est_gain=%.4f | notional=%.2f",
                                            symbol,
                                            execution_result["mode"],
                                            execution_result["quantity"],
                                            format_price(execution_result["entry_price"]),
                                            format_price(execution_result["stop_price"]),
                                            format_price(execution_result["take_profit_price"]),
                                            position_plan.get("reward_risk_ratio", 0.0),
                                            position_plan.get("estimated_loss_at_stop", 0.0),
                                            position_plan.get("estimated_gain_at_target", 0.0),
                                            execution_result.get("notional", 0),
                                        )
                                        log_system_status(
                                            self.logger,
                                            "POSITION_OPENED",
                                            {
                                                "symbol": symbol,
                                                "mode": execution_result["mode"],
                                                "quantity": execution_result["quantity"],
                                                "entry_price": execution_result["entry_price"],
                                                "notional": execution_result.get("notional"),
                                                "score": signal.get("score"),
                                                "zscore": signal_meta.get("zscore"),
                                            },
                                        )
                                    else:
                                        self.logger.warning(
                                            "EXECUTION REJECTED | symbol=%s | reason=%s",
                                            symbol,
                                            execution_result.get("reason", "unknown"),
                                        )

                    if time.time() - last_heartbeat >= heartbeat_interval:
                        active_symbols = self._active_position_symbols()
                        hot_symbols = self.ticker_scanner.get_hot_symbols() if self.ticker_scanner else []
                        self.logger.info(
                            "HEARTBEAT | active_positions=%s/%s | active_symbols=%s | hot_symbols=%s | balance=%.4f USDT | last_symbol=%s | last_price=%.4f",
                            len(active_symbols),
                            self.max_open_positions,
                            ",".join(active_symbols) if active_symbols else "NONE",
                            ",".join(hot_symbols[:10]) if hot_symbols else "NONE",
                            self.risk_manager.balance,
                            symbol,
                            market.get("close", market.get("price", 0.0)),
                        )
                        last_heartbeat = time.time()

                    error_count = 0
                    if max_loops and loop_count >= max_loops:
                        self.logger.info("MAX LOOPS REACHED | loops_completed=%s | exiting gracefully", loop_count)
                        break

                    elapsed = time.time() - loop_started
                    loop_times.append(elapsed)
                    avg_loop_time = sum(loop_times[-10:]) / min(len(loop_times), 10)

                    if elapsed > loop_interval:
                        self.logger.warning(
                            "Loop execution slow | elapsed=%.3fs | interval=%.3fs | avg_last_10=%.3fs",
                            elapsed,
                            loop_interval,
                            avg_loop_time,
                        )

                    sleep_time = max(0.0, loop_interval - elapsed)
                    if sleep_time > 0:
                        time.sleep(sleep_time)

            except KeyboardInterrupt:
                self.logger.warning("MANUAL STOP RECEIVED | shutting down...")
                break
            except Exception as exc:
                error_count += 1
                self.logger.error(
                    "RUNTIME ERROR | iteration=%s | error_count=%s | exception_type=%s | error=%s",
                    loop_iteration,
                    error_count,
                    type(exc).__name__,
                    str(exc),
                )
                self.logger.debug("Stack trace:\n%s", traceback.format_exc())
                log_system_status(
                    self.logger,
                    "RUNTIME_ERROR",
                    {
                        "iteration": loop_iteration,
                        "error_count": error_count,
                        "exception_type": type(exc).__name__,
                        "error_message": str(exc),
                    },
                )
                if error_count > 10:
                    self.logger.critical("Too many consecutive errors, shutting down...")
                    break
                time.sleep(3)

        total_runtime = time.time() - self.started_at
        avg_loop_time = sum(loop_times) / len(loop_times) if loop_times else 0
        self.logger.info("=" * 80)
        self.logger.info(
            "BOT SHUTDOWN | total_loops=%s | avg_loop_time=%.3fs | total_errors=%s | runtime=%.2fs",
            loop_count,
            avg_loop_time,
            error_count,
            total_runtime,
        )
        self.logger.info("Shutdown timestamp: %s", datetime.now(timezone.utc).isoformat())
        self.logger.info("=" * 80)


def main() -> None:
    config = load_config()
    app = TradingApplication(config)
    app.run()


if __name__ == "__main__":
    main()
