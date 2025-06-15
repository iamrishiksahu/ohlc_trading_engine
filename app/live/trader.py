import asyncio
import json
import os
import time
import pandas as pd
from datetime import time, datetime, timedelta
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws
from ..strategies.StrategyBase import StrategyBase, StrategySignal
from ..strategies.SB_VOL import StrategySBVOL
from ..utils.Logger import Logger
from ..utils.FileUtility import FileUtility
from ..ActionScheduler import ActionScheduler, ActionSchedulerParams

class LiveTrader:
    def __init__(self, config, fyers, strategy:StrategyBase=None):
        self.fyers: fyersModel.FyersModel = fyers
        self.config = config
        self.instance_name = ""
        self.symbol = ""
        self.lot_size = ""
        self.interval = 0  # string format as per Fyers: '1', '5', etc.
        self.strategy = strategy
        self.candles = []
        self.active_position = None
        self.current_position = 0
        self.is_started = False

    def on_data(self, df):
        if self.is_started is False:
            return
        
        signal = self.strategy.process(df)
        self.log(f"TRADE_SIGNAL: {signal}")
        
        if signal == StrategySignal.NONE:
            return
        
        elif signal == StrategySignal.BUY:
            order_qty = self.lot_size
            if self.current_position < 0:
                order_qty += -1 * self.current_position 
            self.log(f"lot_size: {self.lot_size} |current_position: {self.current_position} | order_qty: {order_qty}")
            self.place_order(order_qty)
                
        elif signal == StrategySignal.SELL:
            order_qty = self.lot_size
            if self.current_position > 0:
                order_qty += self.current_position 
            self.log(f"lot_size: {self.lot_size} |current_position: {self.current_position} | order_qty: {order_qty}")
            self.place_order(order_qty)
                        
    def place_order(self, order_qty):
        return
        
        side = 1 if order_qty > 0 else -1
        
        order = {
            "symbol": self.symbol,
            "qty": order_qty,
            "type": 2, # market order
            "side": side,
            "productType": "MARGIN",
            "limitPrice": 0,
            "stopPrice": 0,
            "disclosedQty": 0,
            "validity": "DAY",
            "offlineOrder": False,
            "orderTag": "SB_VOL_FYERS_API"
        }
        response = self.fyers.place_order(order)
        
        if response.get("s") == "ok":
            self.log(f"Market order {response.get("id")} sent successfully, assuming filled!")
            self.current_position = order_qty
        else:
            self.log_error(f"Order sending failed {response}")
            
    def get_5_day_range_ending_last_closed_candle(self, interval_minutes: int):
        # Step 1: Avoid landing exactly at the next candle's open time
        simulated_date_str="12-06-2025"
        simulated_time_str="09:15"
        now = datetime.strptime(f"{simulated_date_str} {simulated_time_str}", "%d-%m-%Y %H:%M")
        
        # now = datetime.now()
        adjusted_now = now - timedelta(seconds=1)

        # Step 2: Align to the most recent fully closed candle
        minute_bucket = (adjusted_now.minute // interval_minutes) * interval_minutes
        end = adjusted_now.replace(minute=minute_bucket, second=0, microsecond=0)

        if end > adjusted_now:
            end -= timedelta(minutes=interval_minutes)

        # Step 3: Start 5 days before the END
        start = end - timedelta(days=5)

        # Step 4: Convert to UNIX timestamps
        return int(start.timestamp()), int(end.timestamp())

            
    def run(self):

        range_from, range_to = self.get_5_day_range_ending_last_closed_candle(interval_minutes=30)
    
        params = {
            "symbol": self.symbol,
            "resolution": 30,
            "date_format": "0",
            "range_from": range_from,
            "range_to": range_to,
            "cont_flag": "1"
        }

        data = self.fyers.history(params)
        if not data["candles"]:
            self.log_error("Did not receive ohlc data. Skipping this run.")
            return
        
        df = pd.DataFrame(data['candles'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        self.log(df.head())
        self.on_data(df)
        
    def load_saved_state(self):
        self.log("Looking for saved state")
        
        try:
            if FileUtility.checkIfFileExists("./state.json")["data"] is not True:
                self.log("No state file found. Assuming no saved state.")
                return
            state_data = FileUtility.readFile("./state.json")["data"]

            saved_state = json.loads(state_data)
            self.log(saved_state)
            
            if self.instance_name in saved_state:
                self.log(f"Saved state found for {self.instance_name}.")
                self.current_position = saved_state[self.instance_name]["current_position"] or 0
                self.log(f"Successfully loaded the current position as {self.current_position}")
            else:
                self.log("No saved state found.")
            
        except Exception as e:
            self.log(f"Error loading saved state, assuming no saved state. {e}")
            
    def load_config(self) -> bool:
        try:
            self.instance_name = self.config["instance_name"]
            self.lot_size = self.config["lot_size"]
            self.symbol = self.config["symbol"]
            self.interval = self.config["interval"]
        except Exception as e:
            self.log(f"Error loading strategy config: {e}")
            return False
        
        return True
        

    def start(self):
        self.log("Starting Live Trader")
        
        if not self.load_config():
            return
        
        if not self.validate():
            self.log("Validation failed. Stoping Live Trader")
            return
        
        self.is_started = True
        
        self.load_saved_state()
        
        self.log("Live Trader Started")
        
        action_scheduler_params = ActionSchedulerParams(
            start_time=time(self.config["start_time"][0],self.config["start_time"][1]), 
            end_time=time(self.config["end_time"][0],self.config["end_time"][1]), 
            interval=self.config["interval"]
            )
        action_scheduler = ActionScheduler(action_scheduler_params)
        action_scheduler.schedule(self.run)

        
    def validate(self) -> bool:
        if self.strategy is None:
            self.log_error("No strategy object provided to live trader")
            return False
        
        if not self.strategy.is_valid:
            self.log_error("Strategy object provided to live trader found invalid")
            return False
        
        return True
    
    def log(self, content):
        Logger.log(f"LiveTrader::{self.instance_name}:: {content}")
        
    def log_error(self, content):
        Logger.error(f"LiveTrader::{self.instance_name}:: {content}")