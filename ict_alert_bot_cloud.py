import yfinance as yf
import pandas as pd
import time
import pytz
from datetime import datetime
from telegram import Bot

# ======================
# 🔧 AYARLAR
# ======================
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # Render'da Environment Variable olarak eklenecek
CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"  # kendi chat id'n
SYMBOLS = [
    "USDCHF=X", "USDJPY=X", "USDCAD=X", "XAUUSD=X",
    "AUDNZD=X", "AUDCAD=X", "AUDUSD=X", "AUDCHF=X",
    "EURUSD=X", "EURGBP=X", "EURAUD=X", "EURCHF=X",
    "EURNZD=X", "EURCAD=X", "GBPUSD=X", "GBPJPY=X",
    "GBPCHF=X", "GBPAUD=X", "GBPCAD=X", "GBPNZD=X",
    "NZDUSD=X", "NZDCAD=X", "NZDCHF=X", "CADCHF=X"
]

TIMEFRAMES = {"1d": "Günlük", "1wk": "Haftalık", "1mo": "Aylık"}
CHECK_INTERVAL = 900  # saniye (15 dk)
bot = Bot(token=TELEGRAM_TOKEN)

# ======================
# 🧠 Fonksiyonlar
# ======================
def fetch_data(symbol, timeframe):
    try:
        df = yf.download(symbol, period="3mo", interval=timeframe)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"Veri alınamadı: {symbol} ({timeframe}) - {e}")
        return None


def detect_fvg(df):
    fvg_zones = []
    for i in range(2, len(df)):
        a = df.iloc[i - 2]
        b = df.iloc[i - 1]
        c = df.iloc[i]
        # Bullish FVG
        if a.high < c.low:
            fvg_zones.append(("Bullish", a.high, c.low, df.index[i]))
        # Bearish FVG
        elif a.low > c.high:
            fvg_zones.append(("Bearish", c.high, a.low, df.index[i]))
    return fvg_zones


def check_fvg_touch(df, fvg_zones):
    last_candle = df.iloc[-1]
    for direction, top, bottom, date in fvg_zones:
        if direction == "Bullish" and last_candle.low <= top <= last_candle.high:
            return f"🟢 Bullish FVG teması ({df.index[-1].strftime('%Y-%m-%d')})"
        elif direction == "Bearish" and last_candle.low <= bottom <= last_candle.high:
            return f"🔴 Bearish FVG teması ({df.index[-1].strftime('%Y-%m-%d')})"
    return None


def check_high_low_break(df):
    if len(df) < 2:
        return None
    prev = df.iloc[-2]
    last = df.iloc[-1]
    if last.high > prev.high:
        return "📈 Önceki mumun HIGH kırıldı"
    elif last.low < prev.low:
        return "📉 Önceki mumun LOW kırıldı"
    return None


# ======================
# 🚀 Ana Döngü
# ======================
def run_bot():
    print("ICT Forex Alert Bot (cloud) başlatıldı.")
    while True:
        for symbol in SYMBOLS:
            for tf, tf_name in TIMEFRAMES.items():
                df = fetch_data(symbol, tf)
                if df is None or len(df) < 3:
                    continue

                fvg_zones = detect_fvg(df)
                fvg_alert = check_fvg_touch(df, fvg_zones)
                hl_alert = check_high_low_break(df)

                if fvg_alert or hl_alert:
                    msg = f"⚡ {symbol.replace('=X', '')} | {tf_name}\n"
                    if fvg_alert:
                        msg += f"{fvg_alert}\n"
                    if hl_alert:
                        msg += f"{hl_alert}"
                    try:
                        bot.send_message(chat_id=CHAT_ID, text=msg)
                    except Exception as e:
                        print(f"Telegram hatası: {e}")
                time.sleep(2)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run_bot()
