import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import ta

# === Load Data ===
df = pd.read_csv("./outputs/historical_data/sadf.csv")
df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
df['datetime'] = pd.to_datetime(df['datetime'])

# === Parameters ===
period = 10
multiplier = 3

# === ATR Calculation ===
def calculate_atr(df, period):
    return ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=period)

# === SuperTrend Calculation ===
src = (df['high'] + df['low']) / 2
atr = calculate_atr(df, period)
up = src - multiplier * atr
dn = src + multiplier * atr

trend = []
up_final = []
dn_final = []
signals = []
curr_trend = 1  # Initial trend

for i in range(len(df)):
    if i == 0:
        up_final.append(up.iloc[i])
        dn_final.append(dn.iloc[i])
        trend.append(curr_trend)
        signals.append(None)
        continue

    prev_close = df['close'].iloc[i - 1]
    prev_up = up_final[-1]
    prev_dn = dn_final[-1]

    curr_up = up.iloc[i]
    curr_dn = dn.iloc[i]

    new_up = max(curr_up, prev_up) if prev_close > prev_up else curr_up
    new_dn = min(curr_dn, prev_dn) if prev_close < prev_dn else curr_dn

    if trend[-1] == -1 and df['close'].iloc[i] > prev_dn:
        curr_trend = 1
        signals.append('BUY')
    elif trend[-1] == 1 and df['close'].iloc[i] < prev_up:
        curr_trend = -1
        signals.append('SELL')
    else:
        curr_trend = trend[-1]
        signals.append(None)

    up_final.append(new_up)
    dn_final.append(new_dn)
    trend.append(curr_trend)

# === Append results to df ===
df['supertrend_up'] = up_final
df['supertrend_dn'] = dn_final
df['supertrend_trend'] = trend
df['supertrend_signal'] = signals

# === Plot (only actual data points, categorical axis) ===
plot_df = df.tail(500)  # last 100 rows
x = list(range(len(plot_df)))
labels = plot_df['datetime'].dt.strftime('%Y-%m-%d %H:%M')
close = plot_df['close']
up_line = plot_df['supertrend_up']
dn_line = plot_df['supertrend_dn']

plt.figure(figsize=(15, 6))
plt.plot(x, close, label='Close Price', color='black', linewidth=1)
plt.plot(x, up_line, label='SuperTrend UP', color='green', linestyle='--')
plt.plot(x, dn_line, label='SuperTrend DOWN', color='red', linestyle='--')

# Buy/Sell markers
for i in x:
    signal = plot_df['supertrend_signal'].iloc[i]
    price = close.iloc[i]
    if signal == 'BUY':
        plt.scatter(i, price, marker='^', color='green', s=100, label='BUY Signal' if i == 0 else "")
    elif signal == 'SELL':
        plt.scatter(i, price, marker='v', color='red', s=100, label='SELL Signal' if i == 0 else "")

plt.xticks(ticks=x, labels=labels, rotation=90)
plt.title('SuperTrend Indicator with Trend Flips')
plt.xlabel('Time (each candle = 1 data point)')
plt.ylabel('Price')
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()
