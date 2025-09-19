# trading-bots
Python Bot that helps with Trading in-out

#Purpose
- Lightweight alerting script for 1H/4H swing trading on Forex and Index symbols.
- Fetches OHLC data (default: yfinance), computes indicators (EMA50/EMA200, RSI14, MACD),
  and sends notifications via Telegram and Email when entry/exit conditions are met.
- Designed for "notify-only" workflow: the script will NOT place orders — you execute manually.

# Features
- Data source abstraction: default uses yfinance; add a broker adapter if you want broker-provided data.
- Pure-Python indicator implementations (no TA-Lib required).
- Telegram and SMTP email notifications.
- Single-run mode (for cron) and daemon mode (long-running loop).

# Usage
1) Install dependencies:
   pip install pandas numpy yfinance python-telegram-bot==13.18
   (You may already have these; exact versions optional.)

2) Set configuration in the CONFIG dictionary or via environment variables.

3) Run once:
   python swing_trading_alert_bot.py --once

   Or run as a daemon (polling every N seconds):
   python swing_trading_alert_bot.py

# Notes
- yfinance symbol naming: e.g. 'EURUSD=X' for EUR/USD, '^GSPC' for S&P 500, '^GDAXI' for DAX.
- Timeframes supported: '1h' and '4h' (script will resample yfinance data appropriately).
- Test before using on live data. Use --test to send a test message.

# Extendability
- Implement BrokerAdapter.fetch_ohlc(symbol, timeframe) to use your broker's REST API.