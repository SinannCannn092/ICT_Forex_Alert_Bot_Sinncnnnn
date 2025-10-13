#!/usr/bin/env bash
echo "Render ortamında Linux uyumlu dosya yeniden oluşturuluyor..."

# Hatalı dosyayı sil
rm -f ict_alert_bot_cloud.py

# Yeni dosyayı oluştur (Linux formatında)
cat << 'EOF' > ict_alert_bot_cloud.py
import yfinance as yf
import pandas as pd
import time
from telegram import Bot

TELEGRAM_TOKEN = "8336801111:AAEbEWal-fF4Lnf2YvGk03vMadwnmYO0QiU"
CHAT_ID = "7412702622"
SYMBOLS = [
    "USDCHF=X","USDJPY=X","USDCAD=X","XAUUSD=X",
    "AUDNZD=X","AUDCAD=X","AUDUSD=X","AUDCHF=X",
    "EURUSD=X","EURGBP=X","EURAUD=X","EURCHF=X",
    "EURNZD=X","EURCAD=X","GBPUSD=X","GBPJPY=X",
    "GBPCHF=X","GBPAUD=X","GBPCAD=X","GBPNZD=X",
    "NZDUSD=X","NZDCAD=X","NZDCHF=X","CADCHF=X"
]
TIMEFRAMES={"1d":"Günlük","1wk":"Haftalık","1mo":"Aylık"}
CHECK_INTERVAL=900
bot=Bot(token=TELEGRAM_TOKEN)

def fetch_data(symbol,tf):
    try:
        df=yf.download(symbol,period="3mo",interval=tf)
        df.dropna(inplace=True)
        return df
    except: return None

def detect_fvg(df):
    z=[]
    for i in range(2,len(df)):
        a,b,c=df.iloc[i-2],df.iloc[i-1],df.iloc[i]
        if a.high<c.low: z.append(("Bullish",a.high,c.low))
        elif a.low>c.high: z.append(("Bearish",c.high,a.low))
    return z

def check_touch(df,zones):
    l=df.iloc[-1]
    for d,top,bottom in zones:
        if d=="Bullish" and l.low<=top<=l.high: return "🟢 Bullish FVG temas"
        if d=="Bearish" and l.low<=bottom<=l.high: return "🔴 Bearish FVG temas"
    return None

def check_highlow(df):
    if len(df)<2:return None
    p,l=df.iloc[-2],df.iloc[-1]
    if l.high>p.high:return "📈 HIGH kırıldı"
    if l.low<p.low:return "📉 LOW kırıldı"
    return None

def run_bot():
    print("ICT Forex Alert Bot (Render Cloud) aktif ✅")
    while True:
        for s in SYMBOLS:
            for tf,tfname in TIMEFRAMES.items():
                df=fetch_data(s,tf)
                if df is None or len(df)<3: continue
                zones=detect_fvg(df)
                fvg=check_touch(df,zones)
                hl=check_highlow(df)
                if fvg or hl:
                    msg=f"⚡ {s.replace('=X','')} | {tfname}\n"
                    if fvg: msg+=fvg+"\n"
                    if hl: msg+=hl
                    try: bot.send_message(chat_id=CHAT_ID,text=msg)
                    except Exception as e: print(e)
                time.sleep(2)
        time.sleep(CHECK_INTERVAL)

if __name__=="__main__":
    run_bot()
EOF

# Botu başlat
python3 ict_alert_bot_cloud.py
