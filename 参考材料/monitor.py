import ccxt
import requests
import urllib.parse
import pandas as pd
import time
import csv
import os
from datetime import datetime

# ================= 核心配置 =================
BARK_BASE_URL = "https://api.day.app/qQH2uNcLvpFuqfHqykmMCD"
MIN_QUOTE_VOLUME = 50000000
FR_THRESHOLD = -0.001
TIMEFRAME = '5m'
LIMIT = 100
LOG_FILE = "log.txt"  # 日志文件名
CSV_FILE = "paper_trading_signals.csv"  # 纸面实盘信号CSV文件

# 初始化币安
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

def logger(msg):
    """带时间戳的日志记录，同时输出到控制台和文件"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    # 将日志追加到文件，方便网页查看
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_msg + "\n")

def send_bark_alert(title, content):
    """发送 Bark 推送（支持静音破防与详情日志记录）"""
    safe_title = urllib.parse.quote(title)
    safe_content = urllib.parse.quote(content)
    
    # === Bark 进阶参数配置 ===
    # level=critical : 触发 iOS 的“重要警告”（强制突破静音/睡眠模式）
    # sound=alarm    : 使用警报音效（其他可选音效: bell, minuet, calypso 等）
    # volume=10      : 音量拉满 (范围 1-10)
    bark_params = "?level=critical&sound=alarm&volume=10"
    
    try:
        requests.get(f"{BARK_BASE_URL}/{safe_title}/{safe_content}{bark_params}")
        # 优化日志：将具体的入场价、止盈止损和费率等 content 连同标题一起写入日志
        logger(f"🔔 预警已发送: {title}\n{content}")
    except Exception as e:
        logger(f"❌ 推送失败: {e}")

def log_signal_to_csv(symbol, fr, p):
    """将触发的信号记录到本地 CSV 账本中"""
    filename = CSV_FILE
    file_exists = os.path.isfile(filename)
    
    with open(filename, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # 如果是新文件，先写入表头
        if not file_exists:
            writer.writerow(['timestamp', 'symbol', 'funding_rate', 'current_price', 'entry_price', 'sl', 'tp1', 'tp2', 'status'])
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow([timestamp, symbol, fr, p['current_price'], p['entry_price'], p['sl'], p['tp1'], p['tp2'], 'pending'])
        logger(f"📝 信号已记录到 CSV: {symbol}")

def calculate_trade_signals(symbol, ohlcv):
    """
    量化引擎：计算 VWAP、标准差、SL/TP
    """
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['tp_vol'] = df['tp'] * df['volume']
    df['cum_vol'] = df['volume'].cumsum()
    df['cum_tp_vol'] = df['tp_vol'].cumsum()
    vwap_basis = df['cum_tp_vol'] / df['cum_vol']
    
    df['price_diff_sq'] = ((df['tp'] - vwap_basis) ** 2) * df['volume']
    std_dev = (df['price_diff_sq'].cumsum() / df['cum_vol']) ** 0.5
    
    upper_band = vwap_basis + (std_dev * 2)
    lower_band = vwap_basis - (std_dev * 2)
    
    latest = df.iloc[-1]
    current_price = latest['close']
    
    # 逻辑计算
    entry_price = upper_band.iloc[-1]
    recent_high = df['high'].rolling(window=5).max().iloc[-1]
    stop_loss = recent_high * 1.003
    tp1 = vwap_basis.iloc[-1]
    tp2 = lower_band.iloc[-1]
    
    # 触发条件
    is_extreme = current_price > (upper_band.iloc[-1] * 0.998)
    
    return is_extreme, {
        "current_price": current_price,
        "entry_price": entry_price,
        "sl": stop_loss,
        "tp1": tp1,
        "tp2": tp2
    }

def run_scanner():
    logger("🚀 开始全市场扫描...")
    try:
        tickers = exchange.fetch_tickers()
        funding_rates = exchange.fetch_funding_rates()
        target_symbols = []
        
        for symbol, ticker in tickers.items():
            if not symbol.endswith(':USDT'): continue
            quote_volume = ticker.get('quoteVolume', 0)
            if quote_volume is None or quote_volume < MIN_QUOTE_VOLUME: continue
            
            fr_info = funding_rates.get(symbol)
            if not fr_info or fr_info.get('fundingRate') is None: continue
            current_fr = fr_info['fundingRate']
            
            if current_fr <= FR_THRESHOLD:
                target_symbols.append((symbol, current_fr))
        
        logger(f"🔍 筛选完成，发现 {len(target_symbols)} 个活跃妖币。")
        
        for symbol, fr in target_symbols:
            ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=LIMIT)
            if not ohlcv: continue
            is_extreme, p = calculate_trade_signals(symbol, ohlcv)
            
            if is_extreme:
                title = f"🎯 狙击指令: {symbol.split(':')[0]}"
                content = (f"建议入场: < {p['entry_price']:.4f}\n"
                           f"强制止损: {p['sl']:.4f}\n"
                           f"第一止盈: {p['tp1']:.4f}\n"
                           f"第二止盈: {p['tp2']:.4f}\n"
                           f"当前价: {p['current_price']} | 费率: {fr*100:.2f}%")
                send_bark_alert(title, content)
                log_signal_to_csv(symbol.split(':')[0], fr, p)
                
    except Exception as e:
        logger(f"❌ 运行错误: {e}")

if __name__ == "__main__":
    last_heartbeat_day = ""
    
    while True:
        # 心跳检测：每天早上 8 点发一条信息确认系统在线
        now = datetime.now()
        current_day = now.strftime('%Y-%m-%d')
        if now.hour == 8 and current_day != last_heartbeat_day:
            send_bark_alert("🛰️ 系统心跳正常", f"量化战车持续巡逻中...\n当前时间: {now.strftime('%H:%M:%S')}")
            last_heartbeat_day = current_day
            
        run_scanner()
        logger("⏳ 扫描结束，进入 5 分钟 CD 期...")
        time.sleep(300)