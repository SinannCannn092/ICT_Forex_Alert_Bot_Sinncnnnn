# ict_alert_bot_cloud.py
import os
import time
from datetime import datetime
import logging
import pandas as pd
import yfinance as yf
from telegram import Bot

# --------- CONFIG ----------
# Bot token ve chat id environment variable olarak ayarlayın:
# export BOT_TOKEN="..."   (Windows: setx BOT_TOKEN "...")
# export CHAT_ID="..."
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise SystemExit("BOT_TOKEN veya CHAT_ID environment variable olarak ayarlı değil. Lütfen ayarlayın.")

bot = Bot(token=BOT_TOKEN)

# Parite listesi (Yahoo Finans sembol formatı)
symbols = [
 "USDCHF=X","USDJPY=X","USDCAD=X","XAUUSD=X","AUDNZD=X","AUDCAD=X","AUDUSD=X","AUDCHF=X",
 "EURUSD=X","EURGBP=X","EURAUD=X","EURCHF=X","EURNZD=X","EURCAD=X",
 "GBPUSD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","GBPCAD=X","GBPNZD=X",
 "NZDUSD=X","NZDCAD=X","NZDCHF=X","CADCHF=X"
]

timeframes = {
    "1D": {"yf_interval": "1d", "period": "365d"},
    "1W": {"yf_interval": "1wk", "period": "5y"},
    "1M": {"yf_interval": "1mo", "period": "10y"}
}

# Tarama aralığı (saniye). Bulutta 30 dakika makul: 1800
SLEEP_SECONDS = 1800

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --------- HELPERS ----------
def send_telegram(text):
    try:
        bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="Markdown")
        logging.info("Telegram message sent.")
    except Exception as e:
        logging.exception("Telegram gönderilirken hata: %s", e)

def download_ohlc(symbol, interval, period):
    """
    YFinance'tan veriyi indir. Dönen DataFrame index Datetime.
    """
    try:
        df = yf.download(tickers=symbol, period=period, interval=interval, progress=False, threads=False)
        if df is None or df.empty:
            return None
        # Ensure columns: Open,High,Low,Close,Volume
        return df[['Open','High','Low','Close','Volume']].dropna()
    except Exception as e:
        logging.exception("YFinance indirirken hata: %s", e)
        return None

def check_prev_candle_break(df):
    """
    Son 3 kapalı mum varken:
    prev = df.iloc[-3], curr = df.iloc[-2]
    Eğer curr.high > prev.high => breakout up
    Eğer curr.low < prev.low => breakout down
    """
    if len(df) < 3:
        return None
    prev = df.iloc[-3]
    curr = df.iloc[-2]
    msgs = []
    if curr['High'] > prev['High']:
        msgs.append(("breakout_up", prev['High'], curr['High']))
    if curr['Low'] < prev['Low']:
        msgs.append(("breakout_down", prev['Low'], curr['Low']))
    return msgs if msgs else None

def detect_fvg_and_touch(df):
    """
    FVG detection according to your picture/definition.
    Use four last closed candles A,B,C,D -> indices [-4,-3,-2,-1]
    - Bullish FVG if A.low > C.high  -> gap (C.high, A.low)
    - Bearish FVG if A.high < C.low -> gap (A.high, C.low)
    Then check if D (the candle after C) 'touches' the gap:
      - touching means its High/Low (or Close) enters gap range.
    Returns list of tuples describing matches.
    """
    if len(df) < 4:
        return None
    A = df.iloc[-4]
    B = df.iloc[-3]
    C = df.iloc[-2]
    D = df.iloc[-1]
    results = []

    # Bullish FVG
    if A['Low'] > C['High']:
        gap_low = C['High']
        gap_high = A['Low']
        # D touches gap if any part of candle enters gap
        if (D['High'] >= gap_low) and (D['Low'] <= gap_high):
            results.append(("bullish_fvg_touch", gap_low, gap_high, A.name, B.name, C.name, D.name))

    # Bearish FVG
    if A['High'] < C['Low']:
        gap_low = A['High']
        gap_high = C['Low']
        if (D['High'] >= gap_low) and (D['Low'] <= gap_high):
            results.append(("bearish_fvg_touch", gap_low, gap_high, A.name, B.name, C.name, D.name))

    return results if results else None

# --------- MAIN LOOP ----------
def scan_all():
    for symbol in symbols:
        for tf_name, tf_conf in timeframes.items():
            try:
                df = download_ohlc(symbol, tf_conf["yf_interval"], tf_conf["period"])
                if df is None or df.empty:
                    logging.warning("Veri yok: %s %s", symbol, tf_name)
                    continue

                # Ensure we have at least 4 closed candles for FVG check and 3 for breakout check
                # Note: yfinance returns last partial candle sometimes; we rely on full rows produced by period/interval.
                # Check prev candle breakout (using last two completed candles)
                breakout = check_prev_candle_break(df)
                if breakout:
                    for b in breakout:
                        kind, prev_val, curr_val = b
                        # Format mesaj
                        if kind == "breakout_up":
                            text = f"*{symbol}* `{tf_name}` — *Breakout Up*\nÖnceki mum high: {prev_val:.5f}\nSon mum high: {curr_val:.5f}\nZaman: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
                        else:
                            text = f"*{symbol}* `{tf_name}` — *Breakout Down*\nÖnceki mum low: {prev_val:.5f}\nSon mum low: {curr_val:.5f}\nZaman: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
                        send_telegram(text)

                # Check FVG formation & touch using last 4 candles
                fvg = detect_fvg_and_touch(df)
                if fvg:
                    for f in fvg:
                        kind, gap_low, gap_high, A_time, B_time, C_time, D_time = f
                        text = (f"*{symbol}* `{tf_name}` — *{kind.upper()}*\n"
                                f"Gap range: {gap_low:.5f} — {gap_high:.5f}\n"
                                f"A: {A_time}, B: {B_time}, C: {C_time}, Touch candle (D): {D_time}\n"
                                f"Zaman: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
                        send_telegram(text)

                # küçük sleep her sembol-zaman aralığı arasında aşırı istek göndermemek için
                time.sleep(1.0)

            except Exception as e:
                logging.exception("Tararken hata: %s %s -> %s", symbol, tf_name, e)

if __name__ == "__main__":
    logging.info("ICT Forex Alert Bot (cloud) başlatıldı.")
    while True:
        try:
            scan_all()
            logging.info("Tüm semboller tarandı. %d saniye bekleniyor...", SLEEP_SECONDS)
            time.sleep(SLEEP_SECONDS)
        except Exception as e:
            logging.exception("Ana döngü hatası: %s", e)
            time.sleep(60)
