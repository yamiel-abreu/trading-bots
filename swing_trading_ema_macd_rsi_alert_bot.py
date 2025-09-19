"""
Swing Trading Alert Bot (MACD + RSI Strategy)
--------------------------------------------
Strategy:
- Uses EMA(50/200), MACD, and RSI to generate entry/exit signals.
- ATR-based Stop-Loss (SL) and Take-Profit (TP) suggestions included.

Notifications:
- Alerts are sent via Telegram and Email.
- Dry run mode available (prints only, no notifications).

Usage:
    python swing_trading_alert_bot.py --once      # Run once and exit
    python swing_trading_alert_bot.py --test      # Send test notification
    python swing_trading_alert_bot.py             # Run continuously (for cron/Docker)

Environment variables required:
- TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
- EMAIL_USER, EMAIL_PASS, EMAIL_TO
- DRY_RUN=true (optional, prevents sending messages)
"""

import os
import argparse
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import smtplib
from email.mime.text import MIMEText

CONFIG = {
    "dry_run": False
}

# ==============================
# Notification Functions
# ==============================
def send_telegram(message: str):
    if CONFIG['dry_run']:
        print(f"[DRY RUN] Telegram → {message}")
        return
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[WARN] Telegram not configured")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat_id, "text": message})
    except Exception as e:
        print(f"[ERROR] Telegram send failed: {e}")


def send_email(subject: str, body: str):
    if CONFIG['dry_run']:
        print(f"[DRY RUN] Email → {subject}: {body}")
        return
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    to = os.getenv("EMAIL_TO")
    if not user or not password or not to:
        print("[WARN] Email not configured")
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(user, password)
            server.sendmail(user, to, msg.as_string())
    except Exception as e:
        print(f"[ERROR] Email send failed: {e}")


# ==============================
# Indicators
# ==============================
def EMA(series, period):
    return series.ewm(span=period, adjust=False).mean()


def MACD(df):
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df


def RSI(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def ATR(df, period=14):
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    tr = df[['H-L','H-PC','L-PC']].max(axis=1)
    return tr.rolling(period).mean()


# ==============================
# Strategy with Entry/Exit + SL/TP
# ==============================
class MACDRSIStrategy:
    def __init__(self):
        self.position = None

    def check(self, df):
        df['EMA50'] = EMA(df['Close'], 50)
        df['EMA200'] = EMA(df['Close'], 200)
        df['RSI'] = RSI(df['Close'])
        df = MACD(df)
        df['ATR'] = ATR(df)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        messages = []
        close = last['Close']
        atr = last['ATR']

        # Long Entry
        if last['EMA50'] > last['EMA200'] and prev['MACD'] < prev['Signal'] and last['MACD'] > last['Signal'] and last['RSI'] > 50:
            if self.position != 'long':
                self.position = 'long'
                sl = close - 1.5 * atr
                tp = close + 3 * atr
                messages.append(f"📈 LONG entry signal | SL: {sl:.4f} | TP: {tp:.4f}")

        # Long Exit
        if self.position == 'long' and prev['MACD'] > prev['Signal'] and last['MACD'] < last['Signal']:
            self.position = None
            messages.append("⚠️ LONG exit signal")

        # Short Entry
        if last['EMA50'] < last['EMA200'] and prev['MACD'] > prev['Signal'] and last['MACD'] < last['Signal'] and last['RSI'] < 50:
            if self.position != 'short':
                self.position = 'short'
                sl = close + 1.5 * atr
                tp = close - 3 * atr
                messages.append(f"📉 SHORT entry signal | SL: {sl:.4f} | TP: {tp:.4f}")

        # Short Exit
        if self.position == 'short' and prev['MACD'] < prev['Signal'] and last['MACD'] > last['Signal']:
            self.position = None
            messages.append("⚠️ SHORT exit signal")

        return messages


# ==============================
# Main Runner
# ==============================
def main(one_shot=False, test=False):
    ticker = "EURUSD=X"
    interval = "1h"

    if test:
        send_telegram("✅ Test Telegram Alert")
        send_email("✅ Test Email", "This is a test notification.")
        return

    df = yf.download(ticker, period="90d", interval=interval)
    if df.empty:
        print("No data fetched")
        return

    strat = MACDRSIStrategy()
    signals = strat.check(df)

    for sig in signals:
        msg = f"{ticker} ({interval}) → {sig}"
        print(msg)
        send_telegram(msg)
        send_email("Trading Alert", msg)

    if not one_shot:
        print("Run completed (loop/cron handles rerun).")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Swing trading alert bot (MACD+RSI)")
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--test', action='store_true', help='Send test notifications')
    args = parser.parse_args()

    CONFIG['dry_run'] = os.getenv('DRY_RUN', str(CONFIG['dry_run'])).lower() in ('1','true','yes')

    try:
        main(one_shot=args.once, test=args.test)
    except KeyboardInterrupt:
        print("Interrupted by user")
