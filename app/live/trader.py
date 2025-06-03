import asyncio
import json
import os
import time
from datetime import datetime
from strategies.SB_VOL import StrategySBVOL
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws
from utils.Logger import Logger

class LiveTrader:
    def __init__(self, fyers, symbol='NSE:RELIANCE-EQ', interval='5', strategy=None):
        self.fyers = fyers
        self.symbol = symbol
        self.interval = interval  # string format as per Fyers: '1', '5', etc.
        self.strategy = strategy or StrategySBVOL()
        self.candles = []
        self.active_position = None

    def on_message(self, message):
        if message.get('symbol') != self.symbol:
            return

        candles = message.get('candles')
        if candles:
            for candle in candles:
                ts, o, h, l, c, v = candle
                self._update_candle(ts, o, h, l, c, v)

    def _update_candle(self, ts, o, h, l, c, v):
        timestamp = datetime.fromtimestamp(ts)
        candle = {
            'timestamp': timestamp,
            'open': o,
            'high': h,
            'low': l,
            'close': c,
            'volume': v
        }

        if self.candles and self.candles[-1]['timestamp'] == timestamp:
            self.candles[-1] = candle
        else:
            self.candles.append(candle)

        df = self._candles_df()
        result = self.strategy.calculate(df)

        if result.iloc[-1]['buy_signal']:
            self._place_order('BUY')
        elif result.iloc[-1]['sell_signal']:
            self._place_order('SELL')

    def _place_order(self, side):
        Logger.log(f"Placing order: {side}", type=Logger.LogType.INFO)
        if self.active_position != side:
            # Close existing position if any
            if self.active_position:
                Logger.log(f"Closing {self.active_position} position", type=Logger.LogType.INFO)
                # TODO: place exit order

            # Place new order
            Logger.log(f"Entering {side} position", type=Logger.LogType.INFO)
            # TODO: place entry order via self.fyers.place_order()
            self.active_position = side

    def _candles_df(self):
        import pandas as pd
        return pd.DataFrame(self.candles)

    def start(self):
        Logger.log("Starting Live Trader", type=Logger.LogType.INFO)
        socket = data_ws.FyersDataSocket(
            access_token=self.fyers.access_token,
            log_path=os.path.join("logs", "fyers_ws.log")
        )
        socket.on_message = self.on_message
        socket.subscribe([self.symbol], self.interval)
        socket.connect()


def run():
    # Assumes you have a fyers instance that is authenticated
    from auth.fyers_auth import get_authenticated_fyers
    fyers = get_authenticated_fyers()
    trader = LiveTrader(fyers=fyers, symbol='NSE:RELIANCE-EQ', interval='5')
    trader.start()

if __name__ == "__main__":
    run()
