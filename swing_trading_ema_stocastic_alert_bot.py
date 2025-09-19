"""
Swing Trading Stochastic Bot
----------------------------
Strategy:
- Uses EMA(50/200) trend filter with Stochastic oscillator.
- Long entry when price is in uptrend and Stochastic %K crosses %D below 20.
- Short entry when price is in downtrend and Stochastic %K crosses %D above 80.
- Exit alerts when Stochastic crosses in the opposite zone.
- ATR-based Stop-Loss (SL) and Take-Profit (TP) suggestions included.

Notifications:
- Alerts are sent via Telegram and Email.
- Dry run mode available (prints only, no notifications).

Usage:
    python swing_trading_stochastic_bot.py --once      # Run once and exit
    python swing_trading_stochastic_bot.py --test      # Send test notification
    python swing_trading_stochastic_bot.py             # Run continuously (for cron/Docker)

Environment variables required:
- TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
- EMAIL_USER, EMAIL_PASS, EMAIL_TO
- DRY_RUN=true (optional, prevents sending messages)
"""

import os
import argparse
import pandas as pd
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


def stochastic(df, k=14, d=3):
    low_min = df['Low'].rolling(window=k).min()
    high_max = df['High'].rolling(window=k).max()
    df['%K'] = 100 * (df['Close'] - low_min) / (high_max - low_min)
    df['%D'] = df['%K'].rolling(window=d).mean()
    return df


def ATR(df, period=14):
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    tr = df[['H-L','H-PC','L-PC']].max(axis=1)
    return tr.rolling(period).mean()


# ==============================
# Strategy with Entry/Exit + SL/TP
# ==============================
class StochasticStrategy:
    def __init__(self):
        self.position = None

    def check(self, df):
        df['EMA50'] = EMA(df['Close'], 50)
        df['EMA200'] = EMA(df['Close'], 200)
        df = stochastic(df)
        df['ATR'] = ATR(df)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        messages = []
        close = last['Close']
        atr = last['ATR']

        # Long Entry
        if last['EMA50'] > last['EMA200'] and prev['%K'] < prev['%D'] and last['%K'] > last['%D'] and last['%K'] < 20:
            if self.position != 'long':
                self.position = 'long'
                sl = close - 1.5 * atr
                tp = close + 3 * atr
                messages.append(f"📈 LONG entry signal | SL: {sl:.4f} | TP: {tp:.4f}")

        # Long Exit
        if self.position == 'long' and prev['%K'] > prev['%D'] and last['%K'] < last['%D'] and last['%K'] > 80:
            self.position = None
            messages.append("⚠️ LONG exit signal")

        # Short Entry
        if last['EMA50'] < last['EMA200'] and prev['%K'] > prev['%D'] and last['%K'] < last['%D'] and last['%K'] > 80:
            if self.position != 'short':
                self.position = 'short'
                sl = close + 1.5 * atr
                tp = close - 3 * atr
                messages.append(f"📉 SHORT entry signal | SL: {sl:.4f} | TP: {tp:.4f}")

        # Short Exit
        if self.position == 'short' and prev['%K'] < prev['%D'] and last['%K'] > last['%D'] and last['%K'] < 20:
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

    strat = StochasticStrategy()
    signals = strat.check(df)

    for sig in signals:
        msg = f"{ticker} ({interval}) → {sig}"
        print(msg)
        send_telegram(msg)
        send_email("Trading Alert", msg)

    if not one_shot:
        print("Run completed (loop/cron handles rerun).")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Swing trading stochastic bot")
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--test', action='store_true', help='Send test notifications')
    args = parser.parse_args()

    CONFIG['dry_run'] = os.getenv('DRY_RUN', str(CONFIG['dry_run'])).lower() in ('1','true','yes')

    try:
        main(one_shot=args.once, test=args.test)
    except KeyboardInterrupt:
        print("Interrupted by user")
