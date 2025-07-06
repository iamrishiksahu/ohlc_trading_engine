import pandas as pd
import numpy as np
import ta
from enum import Enum
from dataclasses import dataclass
from ..utils.Logger import Logger
import ta.volatility
from .StrategyBase import StrategyBase
from ..common.enums import StrategySignal
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

@dataclass
class SBVolParams:
    atr_period: int
    multiplier: float
    use_true_atr: bool = True

class StrategySBVOL(StrategyBase):
    def __init__(self, params: SBVolParams, interval: int):
        self.strategy_params = params
        self.is_valid = False
        
        self.interval = interval

    def process_ohlc(self, df: pd.DataFrame, symbol: str) -> tuple[StrategySignal, str]:
        if not self.is_valid:
            return
        
        src = (df['high'] + df['low']) / 2
        atr = self.calculate_atr(df)

        up = src - self.strategy_params.multiplier * atr
        dn = src + self.strategy_params.multiplier * atr

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
                signals.append(StrategySignal.NONE)
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
                signals.append(StrategySignal.BUY)
            elif trend[-1] == 1 and df['close'].iloc[i] < prev_up:
                curr_trend = -1
                signals.append(StrategySignal.SELL)
            else:
                curr_trend = trend[-1]
                signals.append(StrategySignal.NONE)

            up_final.append(new_up)
            dn_final.append(new_dn)
            trend.append(curr_trend)

        # === Append results to df ===
        df['supertrend_up'] = up_final
        df['supertrend_dn'] = dn_final
        df['supertrend_trend'] = trend
        df['supertrend_signal'] = signals

        trend_series = pd.Series(trend, index=df.index)
        

        signal = StrategySignal.NONE
        if trend_series.iloc[-1] == 1 and trend_series.shift(1).iloc[-1] == -1:
            signal = StrategySignal.BUY
        elif trend_series.iloc[-1] == -1 and trend_series.shift(1).iloc[-1] == 1:
            signal = StrategySignal.SELL

        Logger.log(f"SB_VOL:: candle: {df["datetime"].iloc[-1]}, last_trend: {trend_series.iloc[-1]}, curr_trend: {trend_series.shift(1).iloc[-1]}, up: {up_final[-1]}, dn: {dn_final[-1]}, signal: {signals[-1]}")
        return signals[-1], symbol
    
    def calculate_atr(self, df: pd.DataFrame):
        if self.strategy_params.use_true_atr:
            return ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=self.strategy_params.atr_period)
        else:
            tr = df['high'].combine(df['close'].shift(), lambda h, c: np.maximum(h, c)) - \
                 df['low'].combine(df['close'].shift(), lambda l, c: np.minimum(l, c))
            return tr.rolling(window=self.strategy_params.atr_period).mean()    
    
    def init(self) -> bool:
        for symbol in self.symbols:
            symbol.required_ohlc_length = max(self.strategy_params.atr_period / 10 * symbol.interval / 2, 1)
        
        self.symbols_to_subscribe_live_feed = [] # live feed not required for this strategy
        return self.validate(self.strategy_params)
    
    def validate(self, strategy_params: SBVolParams) -> bool:
        if not isinstance(strategy_params.atr_period, int):
            Logger.error("atr_period must be an integer")
            return
        if not isinstance(strategy_params.multiplier, (int, float)):
            Logger.error("multiplier must be a number")
            return
        if not isinstance(strategy_params.use_true_atr, bool):
            Logger.error("use_true_atr must be a boolean")
            return
        self.is_valid = True
        

        Logger.log(f"required_ohlc_length: {self.required_ohlc_length}")
        Logger.log("Strategy validated successfully")
        
    def plot(self, df: pd.DataFrame):
        df = df.dropna().copy()
        fig, ax = plt.subplots(figsize=(14, 6))

        # Plot candles
        for i in range(len(df)):
            color = 'green' if df['close'].iloc[i] >= df['open'].iloc[i] else 'red'
            ax.plot([df.index[i], df.index[i]], [df['low'].iloc[i], df['high'].iloc[i]], color=color)
            ax.plot([df.index[i], df.index[i]], [df['open'].iloc[i], df['close'].iloc[i]], linewidth=5, color=color)

        # Plot trend bands
        ax.plot(df.index, df['up'], label='Up', color='green', linestyle='--', linewidth=1)
        ax.plot(df.index, df['dn'], label='Down', color='red', linestyle='--', linewidth=1)

        # Plot signals
        buy_signals = df[df['signal'] == StrategySignal.BUY]
        sell_signals = df[df['signal'] == StrategySignal.SELL]

        ax.scatter(buy_signals.index, buy_signals['low'], marker='^', color='green', s=100, label='BUY Signal')
        ax.scatter(sell_signals.index, sell_signals['high'], marker='v', color='red', s=100, label='SELL Signal')

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.set_title("SB VOL Strategy Signals")
        ax.legend()
        ax.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()