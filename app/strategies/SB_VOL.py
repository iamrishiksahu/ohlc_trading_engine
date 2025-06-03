import pandas as pd
import numpy as np
import datetime

class StrategySBVOL:
    def __init__(self, period=10, multiplier=3.0, use_true_atr=True):
        self.period = period
        self.multiplier = multiplier
        self.use_true_atr = use_true_atr

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # Typical price as source
        src = (df['high'] + df['low']) / 2

        # ATR Calculation
        tr = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift()),
            abs(df['low'] - df['close'].shift())
        ], axis=1).max(axis=1)

        atr = tr.rolling(self.period).mean() if self.use_true_atr else tr.expanding().mean()

        up = src - self.multiplier * atr
        dn = src + self.multiplier * atr

        df['trend'] = 1  # Start with uptrend

        up1 = up.shift(1)
        dn1 = dn.shift(1)
        close1 = df['close'].shift(1)

        for i in range(1, len(df)):
            if close1.iloc[i] > up1.iloc[i]:
                up.iloc[i] = max(up.iloc[i], up1.iloc[i])
            else:
                up.iloc[i] = up.iloc[i]

            if close1.iloc[i] < dn1.iloc[i]:
                dn.iloc[i] = min(dn.iloc[i], dn1.iloc[i])
            else:
                dn.iloc[i] = dn.iloc[i]

            if df['trend'].iloc[i - 1] == -1 and df['close'].iloc[i] > dn1.iloc[i]:
                df['trend'].iloc[i] = 1
            elif df['trend'].iloc[i - 1] == 1 and df['close'].iloc[i] < up1.iloc[i]:
                df['trend'].iloc[i] = -1
            else:
                df['trend'].iloc[i] = df['trend'].iloc[i - 1]

        df['buy_signal'] = (df['trend'] == 1) & (df['trend'].shift(1) == -1)
        df['sell_signal'] = (df['trend'] == -1) & (df['trend'].shift(1) == 1)

        return df
