import asyncio
import html
import traceback
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

import ccxt.pro
import pandas as pd
import requests

# ================= 配置 =================
BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "paper_trading_signals.csv"
BARK_BASE_URL = "https://api.day.app/qQH2uNcLvpFuqfHqykmMCD"
SCAN_INTERVAL = 1
OPENED_TIMEOUT_MINUTES = 15
MAX_TRACKING_HOURS = 24
TRADING_FEE_RATE = 0.0005  # 单边手续费
RISK_USDT_PER_TRADE = 10.0
MARKET_LOAD_TIMEOUT = 30.0
PRICE_STALE_SECONDS = 10.0
ENABLE_PROXY_FALLBACK = True
PROXY_URL = "http://127.0.0.1:7890"

WEB_LOG_FILE = BASE_DIR / "tracker_log.html"
MAX_WEB_LOGS = 300

ACTIVE_STATUSES = {"Pending", "Opened", "Opened_TP1"}
FINAL_STATUSES = {"Win", "Loss", "Expired", "Invalid", "Timeout_Closed"}
STATUS_ALIAS = {
    "pending": "Pending",
    "opened": "Opened",
    "opened_tp1": "Opened_TP1",
    "win": "Win",
    "loss": "Loss",
    "expired": "Expired",
    "invalid": "Invalid",
    "timeout_closed": "Timeout_Closed",
}

REQUIRED_COLUMNS = [
    "symbol",
    "timestamp",
    "entry_price",
    "sl",
    "tp1",
    "tp2",
    "status",
]

DEFAULT_EXTRA_COLUMNS = {
    "normalized_symbol": "",
    "opened_time": "",
    "exit_time": "",
    "profit_pct": "",
    "profit_usdt": "",
    "tp1_hit": False,
    "realized_profit_usdt": 0.0,
    "entry_trigger_price": "",
    "invalid_reason": "",
}

web_logs_buffer = []
csv_lock = asyncio.Lock()

exchange: Optional[ccxt.pro.binance] = None


def logger(message: str) -> None:
    """统一日志输出：控制台 + HTML 文件。"""
    global web_logs_buffer
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {message}"
    print(line, flush=True)
    web_logs_buffer.append(line)
    if len(web_logs_buffer) > MAX_WEB_LOGS:
        web_logs_buffer = web_logs_buffer[-MAX_WEB_LOGS:]

    try:
        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="3">
  <title>Tracker Log</title>
  <style>
    body {{ background:#111; color:#d6ffd6; font-family:Menlo,Consolas,monospace; padding:14px; }}
    h3 {{ color:#fff; margin:0 0 12px 0; }}
    .line {{ border-bottom:1px solid #222; padding:3px 0; white-space:pre-wrap; }}
  </style>
</head>
<body>
  <h3>Binance Futures Tracker (Auto Refresh 3s)</h3>
  {"".join(f'<div class="line">{html.escape(x)}</div>' for x in web_logs_buffer)}
</body>
</html>"""
        WEB_LOG_FILE.write_text(html_content, encoding="utf-8")
    except Exception as exc:
        print(
            f"[{now}] [LOGGER_ERROR] 写入 HTML 日志失败: {type(exc).__name__}: {exc}",
            flush=True,
        )


def normalize_status(status: object) -> str:
    raw = str(status).strip()
    if raw in STATUS_ALIAS:
        return STATUS_ALIAS[raw]
    if raw in ACTIVE_STATUSES or raw in FINAL_STATUSES:
        return raw
    return raw


def normalize_symbol_for_futures(raw_symbol: str) -> str:
    """
    将信号 symbol 统一为 CCXT U 本位合约格式。
    示例: XAU/USDT -> XAU/USDT:USDT
    """
    symbol = str(raw_symbol).strip().upper()
    if ":" in symbol:
        return symbol
    if symbol.endswith("/USDT"):
        return f"{symbol}:USDT"
    return symbol


def parse_dt(text: object) -> Optional[datetime]:
    try:
        return datetime.strptime(str(text).strip(), "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def safe_float(value: object, field_name: str) -> float:
    try:
        return float(value)
    except Exception as exc:
        raise ValueError(f"字段 {field_name} 无法转为 float: {value!r}") from exc


def send_bark_alert_sync(title: str, content: str) -> None:
    safe_title = urllib.parse.quote(title)
    safe_content = urllib.parse.quote(content)
    url = f"{BARK_BASE_URL}/{safe_title}/{safe_content}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()


async def send_bark_alert(title: str, content: str) -> None:
    """推送报警，失败时打印详细错误，不吞异常细节。"""
    try:
        await asyncio.to_thread(send_bark_alert_sync, title, content)
        logger(f"[BARK] 推送成功: {title}")
    except Exception as exc:
        logger(f"[BARK_ERROR] {type(exc).__name__}: {exc} | title={title}")


def create_exchange(use_proxy: bool = False) -> ccxt.pro.binance:
    config = {
        "enableRateLimit": True,
        "options": {"defaultType": "future"},
    }
    ex = ccxt.pro.binance(config)
    if use_proxy:
        ex.aiohttp_proxy = PROXY_URL
    return ex


async def init_exchange() -> ccxt.pro.binance:
    """
    初始化交易所连接并加载市场。
    若直连失败且允许代理，则自动尝试 127.0.0.1:7890。
    """
    global exchange
    attempts = [False, True] if ENABLE_PROXY_FALLBACK else [False]
    last_error = None
    for use_proxy in attempts:
        ex = create_exchange(use_proxy=use_proxy)
        try:
            await asyncio.wait_for(ex.load_markets(), timeout=MARKET_LOAD_TIMEOUT)
            exchange = ex
            mode = f"代理 {PROXY_URL}" if use_proxy else "直连"
            logger(f"[INIT] load_markets 成功，网络模式: {mode}")
            return ex
        except Exception as exc:
            last_error = exc
            logger(
                f"[INIT_ERROR] load_markets 失败 ({'proxy' if use_proxy else 'direct'}): "
                f"{type(exc).__name__}: {exc}"
            )
            try:
                await ex.close()
            except Exception:
                pass
    raise RuntimeError(f"初始化交易所失败: {type(last_error).__name__}: {last_error}")


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"CSV 缺少必需字段: {col}")
    for col, default_value in DEFAULT_EXTRA_COLUMNS.items():
        if col not in df.columns:
            df[col] = default_value
    return df


def row_key(row: pd.Series) -> Tuple[str, str]:
    return str(row["symbol"]), str(row["timestamp"])


@dataclass
class TradeContext:
    row: pd.Series
    status: str
    raw_symbol: str
    ccxt_symbol: str
    timestamp_text: str
    signal_time: datetime
    entry_price: float
    sl: float
    tp1: float
    tp2: float
    is_short: bool
    quantity_full: float
    quantity_half: float
    tp1_hit: bool
    realized_profit_usdt: float


def parse_trade_context(row: pd.Series) -> TradeContext:
    status = normalize_status(row["status"])
    raw_symbol = str(row["symbol"]).strip().upper()
    ccxt_symbol = normalize_symbol_for_futures(raw_symbol)
    signal_time = parse_dt(row["timestamp"])
    if signal_time is None:
        raise ValueError(f"timestamp 格式错误: {row['timestamp']!r}")

    entry_price = safe_float(row["entry_price"], "entry_price")
    sl = safe_float(row["sl"], "sl")
    tp1 = safe_float(row["tp1"], "tp1")
    tp2 = safe_float(row["tp2"], "tp2")
    if abs(entry_price - sl) < 1e-12:
        raise ValueError("entry_price 与 sl 相同，无法计算仓位")

    is_short = tp1 < entry_price
    quantity_full = RISK_USDT_PER_TRADE / abs(entry_price - sl)
    quantity_half = quantity_full / 2.0
    tp1_hit = bool(row.get("tp1_hit", False)) or status == "Opened_TP1"
    realized_profit_usdt = float(row.get("realized_profit_usdt", 0.0) or 0.0)

    return TradeContext(
        row=row,
        status=status,
        raw_symbol=raw_symbol,
        ccxt_symbol=ccxt_symbol,
        timestamp_text=str(row["timestamp"]),
        signal_time=signal_time,
        entry_price=entry_price,
        sl=sl,
        tp1=tp1,
        tp2=tp2,
        is_short=is_short,
        quantity_full=quantity_full,
        quantity_half=quantity_half,
        tp1_hit=tp1_hit,
        realized_profit_usdt=realized_profit_usdt,
    )


def calc_pnl_usdt(entry_price: float, exit_price: float, quantity: float, is_short: bool) -> float:
    """
    计算扣除单边手续费后的净盈亏。
    long: (sell*(1-fee) - buy*(1+fee)) * qty
    short: (sell*(1-fee) - buy*(1+fee)) * qty, 但 sell 在 entry，buy 在 exit
    """
    fee = TRADING_FEE_RATE
    if is_short:
        entry_sell = entry_price * (1 - fee)
        exit_buy = exit_price * (1 + fee)
        return (entry_sell - exit_buy) * quantity
    entry_buy = entry_price * (1 + fee)
    exit_sell = exit_price * (1 - fee)
    return (exit_sell - entry_buy) * quantity


def calc_profit_pct(profit_usdt: float, entry_price: float, quantity: float) -> float:
    notional = max(entry_price * quantity, 1e-12)
    return (profit_usdt / notional) * 100.0


class PriceStreamManager:
    """每个 symbol 启一个 watch_ticker 任务，缓存最新价格供策略读取。"""

    def __init__(self, ex: ccxt.pro.binance):
        self.exchange = ex
        self.tasks: Dict[str, asyncio.Task] = {}
        self.latest: Dict[str, Tuple[float, datetime]] = {}
        self.running = True

    async def ensure_symbol(self, symbol: str) -> None:
        if symbol in self.tasks:
            return
        self.tasks[symbol] = asyncio.create_task(self._watch_symbol(symbol))
        logger(f"[WS] 启动价格订阅: {symbol}")

    async def _watch_symbol(self, symbol: str) -> None:
        while self.running:
            try:
                ticker = await self.exchange.watch_ticker(symbol)
                price = ticker.get("last") or ticker.get("close") or ticker.get("bid") or ticker.get("ask")
                if price is None:
                    raise ValueError(f"ticker 缺少价格字段: {ticker}")
                self.latest[symbol] = (float(price), datetime.now())
            except Exception as exc:
                # 关键修复：所有底层异常必须记录类型 + 详细内容
                logger(
                    f"[PRICE_ERROR] symbol={symbol} | {type(exc).__name__}: {exc}\n"
                    f"{traceback.format_exc(limit=3)}"
                )
                await asyncio.sleep(1)

    def get_latest_price(self, symbol: str) -> Optional[float]:
        data = self.latest.get(symbol)
        if not data:
            return None
        price, ts = data
        if (datetime.now() - ts).total_seconds() > PRICE_STALE_SECONDS:
            return None
        return price

    async def close(self) -> None:
        self.running = False
        for task in self.tasks.values():
            task.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)


async def read_signals_df() -> Optional[pd.DataFrame]:
    if not CSV_FILE.exists():
        logger(f"[CSV] 文件不存在，等待创建: {CSV_FILE}")
        return None
    try:
        async with csv_lock:
            df = pd.read_csv(CSV_FILE)
        return ensure_columns(df)
    except Exception as exc:
        logger(f"[CSV_ERROR] 读取失败: {type(exc).__name__}: {exc}")
        return None


async def update_row_by_key(
    key: Tuple[str, str],
    updates: Dict[str, object],
    log_prefix: str,
) -> bool:
    """按 symbol + timestamp 精确更新一行，避免并发写文件互相覆盖。"""
    try:
        async with csv_lock:
            if not CSV_FILE.exists():
                logger(f"[CSV_ERROR] 更新失败，文件不存在: {CSV_FILE}")
                return False
            df = ensure_columns(pd.read_csv(CSV_FILE))
            symbol, timestamp_text = key
            mask = (df["symbol"].astype(str) == symbol) & (df["timestamp"].astype(str) == timestamp_text)
            if not mask.any():
                logger(f"[CSV_WARN] 未找到记录: symbol={symbol}, timestamp={timestamp_text}")
                return False
            idx = df[mask].index[0]
            for col, value in updates.items():
                df.loc[idx, col] = value
            df.to_csv(CSV_FILE, index=False, encoding="utf-8")
        logger(f"{log_prefix} 更新成功: {key} -> {updates}")
        return True
    except Exception as exc:
        logger(f"[CSV_ERROR] 更新失败 key={key} | {type(exc).__name__}: {exc}")
        return False


def is_entry_triggered(last_price: Optional[float], current_price: float, entry: float, is_short: bool) -> bool:
    # 初次无 last_price 时按触价判定，兼容历史逻辑
    if last_price is None:
        return current_price >= entry if is_short else current_price <= entry
    # 有 last_price 时按“穿过”判定
    return (last_price - entry) * (current_price - entry) <= 0


def hit_sl(price: float, sl: float, is_short: bool) -> bool:
    return price >= sl if is_short else price <= sl


def hit_tp(price: float, tp: float, is_short: bool) -> bool:
    return price <= tp if is_short else price >= tp


async def mark_invalid(ctx: TradeContext, reason: str) -> None:
    key = (ctx.raw_symbol, ctx.timestamp_text)
    await update_row_by_key(
        key,
        {
            "status": "Invalid",
            "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "invalid_reason": reason,
            "normalized_symbol": ctx.ccxt_symbol,
        },
        "[INVALID]",
    )
    await send_bark_alert(f"Invalid 标的 {ctx.raw_symbol}", reason)


async def process_signal_row(
    row: pd.Series,
    price_manager: PriceStreamManager,
    symbol_cache: Dict[str, bool],
    last_price_cache: Dict[Tuple[str, str], float],
) -> None:
    try:
        ctx = parse_trade_context(row)
    except Exception as exc:
        raw_symbol = str(row.get("symbol", "UNKNOWN"))
        key = (raw_symbol, str(row.get("timestamp", "")))
        logger(f"[ROW_ERROR] 解析失败 {key}: {type(exc).__name__}: {exc}")
        await update_row_by_key(
            key,
            {
                "status": "Invalid",
                "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "invalid_reason": f"{type(exc).__name__}: {exc}",
            },
            "[INVALID]",
        )
        return

    key = (ctx.raw_symbol, ctx.timestamp_text)

    if ctx.status not in ACTIVE_STATUSES:
        return

    # 严格校验 futures market 是否存在；不存在立即 Invalid，拒绝无效等待
    if ctx.ccxt_symbol not in symbol_cache:
        symbol_cache[ctx.ccxt_symbol] = ctx.ccxt_symbol in exchange.markets
    if not symbol_cache[ctx.ccxt_symbol]:
        reason = f"Binance U本位合约不存在: {ctx.ccxt_symbol}"
        logger(f"[INVALID_SYMBOL] {reason}")
        await mark_invalid(ctx, reason)
        return

    await price_manager.ensure_symbol(ctx.ccxt_symbol)
    current_price = price_manager.get_latest_price(ctx.ccxt_symbol)
    if current_price is None:
        logger(f"[PRICE_WAIT] 暂无最新价格: {ctx.ccxt_symbol}")
        return

    last_price = last_price_cache.get(key)
    last_price_cache[key] = current_price

    # Pending: 15 分钟内穿过 entry 触发开仓，否则 Expired
    if ctx.status == "Pending":
        if datetime.now() - ctx.signal_time > timedelta(minutes=OPENED_TIMEOUT_MINUTES):
            await update_row_by_key(
                key,
                {
                    "status": "Expired",
                    "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "normalized_symbol": ctx.ccxt_symbol,
                },
                "[EXPIRED]",
            )
            await send_bark_alert(
                f"{ctx.raw_symbol} 入场超时",
                f"15分钟未触发入场，已标记 Expired。symbol={ctx.ccxt_symbol}",
            )
            return

        if is_entry_triggered(last_price, current_price, ctx.entry_price, ctx.is_short):
            opened_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await update_row_by_key(
                key,
                {
                    "status": "Opened",
                    "opened_time": opened_time,
                    "normalized_symbol": ctx.ccxt_symbol,
                    "entry_trigger_price": current_price,
                    "tp1_hit": False,
                    "realized_profit_usdt": 0.0,
                    "invalid_reason": "",
                },
                "[OPENED]",
            )
            side = "Short" if ctx.is_short else "Long"
            await send_bark_alert(
                f"{ctx.raw_symbol} 已入场",
                f"方向={side}, entry={ctx.entry_price}, 触发价={current_price}",
            )
        return

    # Opened / Opened_TP1: 先判断 24h 超时强平
    opened_time = parse_dt(row.get("opened_time", "")) or ctx.signal_time
    if datetime.now() - opened_time > timedelta(hours=MAX_TRACKING_HOURS):
        profit_tail = calc_pnl_usdt(ctx.entry_price, current_price, ctx.quantity_half if ctx.tp1_hit else ctx.quantity_full, ctx.is_short)
        total_profit = ctx.realized_profit_usdt + profit_tail
        profit_pct = calc_profit_pct(total_profit, ctx.entry_price, ctx.quantity_full)
        await update_row_by_key(
            key,
            {
                "status": "Timeout_Closed",
                "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "profit_usdt": round(total_profit, 6),
                "profit_pct": round(profit_pct, 6),
                "normalized_symbol": ctx.ccxt_symbol,
            },
            "[TIMEOUT_CLOSED]",
        )
        await send_bark_alert(
            f"{ctx.raw_symbol} 超时平仓",
            f"超过{MAX_TRACKING_HOURS}小时，强制平仓，PnL={total_profit:.4f} USDT",
        )
        return

    # 未到 TP1 前，优先判断 SL；随后处理 TP1/TP2
    if not ctx.tp1_hit:
        if hit_sl(current_price, ctx.sl, ctx.is_short):
            total_profit = calc_pnl_usdt(ctx.entry_price, ctx.sl, ctx.quantity_full, ctx.is_short)
            profit_pct = calc_profit_pct(total_profit, ctx.entry_price, ctx.quantity_full)
            await update_row_by_key(
                key,
                {
                    "status": "Loss",
                    "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "profit_usdt": round(total_profit, 6),
                    "profit_pct": round(profit_pct, 6),
                    "normalized_symbol": ctx.ccxt_symbol,
                },
                "[LOSS]",
            )
            await send_bark_alert(
                f"{ctx.raw_symbol} 止损",
                f"SL={ctx.sl}, 当前={current_price}, PnL={total_profit:.4f} USDT",
            )
            return

        if hit_tp(current_price, ctx.tp2, ctx.is_short):
            # 单 tick 直达 TP2：按“半仓 TP1 + 半仓 TP2”计算，贴合业务定义
            profit_tp1 = calc_pnl_usdt(ctx.entry_price, ctx.tp1, ctx.quantity_half, ctx.is_short)
            profit_tp2 = calc_pnl_usdt(ctx.entry_price, ctx.tp2, ctx.quantity_half, ctx.is_short)
            total_profit = profit_tp1 + profit_tp2
            profit_pct = calc_profit_pct(total_profit, ctx.entry_price, ctx.quantity_full)
            await update_row_by_key(
                key,
                {
                    "status": "Win",
                    "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "tp1_hit": True,
                    "realized_profit_usdt": round(profit_tp1, 6),
                    "profit_usdt": round(total_profit, 6),
                    "profit_pct": round(profit_pct, 6),
                    "normalized_symbol": ctx.ccxt_symbol,
                },
                "[WIN]",
            )
            await send_bark_alert(
                f"{ctx.raw_symbol} 止盈(直达TP2)",
                f"TP1+TP2 完成, 总PnL={total_profit:.4f} USDT",
            )
            return

        if hit_tp(current_price, ctx.tp1, ctx.is_short):
            realized = calc_pnl_usdt(ctx.entry_price, ctx.tp1, ctx.quantity_half, ctx.is_short)
            await update_row_by_key(
                key,
                {
                    "status": "Opened_TP1",
                    "tp1_hit": True,
                    "realized_profit_usdt": round(realized, 6),
                    "normalized_symbol": ctx.ccxt_symbol,
                },
                "[TP1]",
            )
            await send_bark_alert(
                f"{ctx.raw_symbol} 命中 TP1",
                f"半仓止盈完成，已实现={realized:.4f} USDT，剩余仓位移动到保本逻辑。",
            )
            return

    # TP1 后：剩余半仓，SL 上移到入场价（保本），或触发 TP2
    if ctx.tp1_hit:
        if hit_tp(current_price, ctx.tp2, ctx.is_short):
            tail_profit = calc_pnl_usdt(ctx.entry_price, ctx.tp2, ctx.quantity_half, ctx.is_short)
            total_profit = ctx.realized_profit_usdt + tail_profit
            profit_pct = calc_profit_pct(total_profit, ctx.entry_price, ctx.quantity_full)
            await update_row_by_key(
                key,
                {
                    "status": "Win",
                    "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "profit_usdt": round(total_profit, 6),
                    "profit_pct": round(profit_pct, 6),
                    "normalized_symbol": ctx.ccxt_symbol,
                },
                "[WIN]",
            )
            await send_bark_alert(
                f"{ctx.raw_symbol} 命中 TP2",
                f"总PnL={total_profit:.4f} USDT (含TP1已实现)",
            )
            return

        if hit_sl(current_price, ctx.entry_price, ctx.is_short):
            tail_profit = calc_pnl_usdt(ctx.entry_price, ctx.entry_price, ctx.quantity_half, ctx.is_short)
            total_profit = ctx.realized_profit_usdt + tail_profit
            profit_pct = calc_profit_pct(total_profit, ctx.entry_price, ctx.quantity_full)
            await update_row_by_key(
                key,
                {
                    "status": "Win",
                    "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "profit_usdt": round(total_profit, 6),
                    "profit_pct": round(profit_pct, 6),
                    "normalized_symbol": ctx.ccxt_symbol,
                },
                "[BREAKEVEN_EXIT]",
            )
            await send_bark_alert(
                f"{ctx.raw_symbol} 保本离场",
                f"剩余半仓保本，最终PnL={total_profit:.4f} USDT",
            )


async def processing_loop() -> None:
    symbol_cache: Dict[str, bool] = {}
    last_price_cache: Dict[Tuple[str, str], float] = {}
    price_manager = PriceStreamManager(exchange)

    try:
        while True:
            df = await read_signals_df()
            if df is None:
                await asyncio.sleep(SCAN_INTERVAL)
                continue

            df["status"] = df["status"].map(normalize_status)
            active_df = df[df["status"].isin(ACTIVE_STATUSES)].copy()

            if active_df.empty:
                await asyncio.sleep(SCAN_INTERVAL)
                continue

            tasks = [
                asyncio.create_task(
                    process_signal_row(row, price_manager, symbol_cache, last_price_cache)
                )
                for _, row in active_df.iterrows()
            ]
            # 并发处理多个信号，确保单个信号异常不会阻塞全局
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for exc in results:
                if isinstance(exc, Exception):
                    logger(f"[TASK_ERROR] {type(exc).__name__}: {exc}")

            await asyncio.sleep(SCAN_INTERVAL)
    finally:
        await price_manager.close()


async def main() -> None:
    logger("Tracker 启动：Binance U本位信号执行端")
    logger(
        f"参数: SCAN_INTERVAL={SCAN_INTERVAL}s, OPENED_TIMEOUT={OPENED_TIMEOUT_MINUTES}m, "
        f"MAX_TRACKING={MAX_TRACKING_HOURS}h, FEE={TRADING_FEE_RATE}"
    )
    try:
        await init_exchange()
        await processing_loop()
    except Exception as exc:
        logger(
            f"[FATAL] {type(exc).__name__}: {exc}\n"
            f"{traceback.format_exc(limit=8)}"
        )
        await send_bark_alert("Tracker 致命错误", f"{type(exc).__name__}: {exc}")
    finally:
        if exchange is not None:
            try:
                await exchange.close()
            except Exception as exc:
                logger(f"[CLOSE_ERROR] {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
