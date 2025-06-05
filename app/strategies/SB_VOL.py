import pandas as pd
import numpy as np
import ta
from enum import Enum
from dataclasses import dataclass
from utils.Logger import Logger
import ta.volatility
from StrategyBase import StrategyBase, StrategySignal

@dataclass
class SBVolParams:
    atr_period: int
    multiplier: float
    use_true_atr: bool = True

class StrategySBVOL(StrategyBase):
    def __init__(self, params):
        self.params = params
        self.is_valid = False
        self.validate()

        
    def process(self, df) -> StrategySignal:
        if not self.is_valid:
            return
        
        hl2 = (df["high"] + df["low"]) / 2
        atr = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=self.strategy_params.atr_period)
        
        up = hl2 - self.strategy_params.multiplier * atr
        dn = hl2 + self.strategy_params.multiplier * atr

        trend = []
        current_trend = 1

        for i in range(len(df)):
            if i == 0:
                trend.append(current_trend)
                continue

            up1 = max(up[i-1], up[i]) if df["close"][i-1] > up[i-1] else up[i]
            dn1 = min(dn[i-1], dn[i]) if df["close"][i-1] < dn[i-1] else dn[i]

            if current_trend == -1 and df["close"][i] > dn1:
                current_trend = 1
            elif current_trend == 1 and df["close"][i] < up1:
                current_trend = -1

            trend.append(current_trend)

        trend = pd.Series(trend, index=df.index)
        
        signal = StrategySignal.NONE
        
        if (trend == 1) & (trend.shift(1) == -1):
            signal = StrategySignal.BUY
        elif (trend == -1) & (trend.shift(1) == 1):
            signal = StrategySignal.SELL
        
        return signal
        
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
        Logger.log("Strategy validated successfully")