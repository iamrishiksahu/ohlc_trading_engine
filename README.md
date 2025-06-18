# OHLC Trading Engine

This is a robust high-performance trading engine to execute OHLC based trading strategies and backtest them with precise simulation.

## 📌 Features

- 🔍 Candlestick-based signal evaluation
- ⌚ Robust and fail proof Scheduling
- 📈 Volume breakout logic with configurable parameters
- 🔁 Historical data backtesting
- ⚙️ Live execution using **Fyers API**
- 📊 Strategy logic: Detects volume surges and price movements based on historical conditions

## 🛠️ Components

1. **Strategy Core**
    - Parses candle data (OHLCV)
    - Processes OHLC data to generate trade signals

2.  **Live Trader**
    - Uses Fyers API for real-time data and order execution
    - Fail proof robust signal evaluation

3. **Action Scheduler**
    - Efficiently and accurately schedule next runs
    - Maintains and manages overall strategy scheduling

4. **Historical Data Downloader**
    - Powerful module to download large historical data
    - Automatically formats and saves data to CSV for analysis.
    
5.  **Backtester**
    - Simulates the strategy on historical market data
    - Provides basic analytics (PnL, trades, win-rate)

6. **Logger**
    - Exhaustive logging of each and every decision steps
    - Logs entire journey of the application for quick debugging

## 🔧 Configuration

All parameters can be tuned via a configuration file:
- Lookback period
- Volume moving average window
- Entry conditions
- Timeframe

## 🚀 Usage

Using it for any purpose would require a config.json file

This file should be placed only in the project root directory.

`config_sample.json` can be referred to find the schema of the config.

### Running LIVE

```bash
python -m app    
```

### Backtesting

You can also use the same application for backtesting.
All parameters other than backtesting period will be picked up from the config file.

```bash
python -m app --backtest --period [number of days]
```


### Build EXE

To use this application portably, you can create an EXE build and run it on any machine.
```bash
python exe_build_entry.py --onedir
```
