#!/usr/bin/env bash
echo "Render ortamında dosya hazırlanıyor..."
python3 - << 'EOF'
import yfinance as yf
import pandas as pd
import time
from telegram import Bot

TELEGRAM_TOKEN = "BURAYA_TOKENİNİ_YAZ"
CHAT_ID = "BURAYA_CHAT_ID_YAZ"
SYMBOLS = ["EURUSD=X","GBPUSD=X"]
TIMEFRAMES={"1d":"Günlük"}
bot=Bot(token=TELEGRAM_TOKEN)

print("Bot çalışmaya başladı...")

while True:
    for s in SYMBOLS:
        for tf,tfname in TIMEFRAMES.items():
            df=yf.download(s,period="2mo",interval=tf)
            if len(df)<3: continue
            prev, last = df.iloc[-2], df.iloc[-1]
            msg=None
            if last.high>prev.high: msg=f"📈 {s} HIGH kırıldı ({tfname})"
            elif last.low<prev.low: msg=f"📉 {s} LOW kırıldı ({tfname})"
            if msg:
                bot.send_message(chat_id=CHAT_ID,text=msg)
            time.sleep(1)
    time.sleep(300)
EOF
