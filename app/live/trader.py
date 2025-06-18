import json
import time
import pandas as pd
import time as time_module
from datetime import time, datetime, timedelta
from fyers_apiv3 import fyersModel
from ..strategies.StrategyBase import StrategyBase, StrategySignal
from ..utils.Logger import Logger
from ..utils.FileUtility import FileUtility
from ..ActionScheduler import ActionScheduler, ActionSchedulerParams
from ..utils.Constants import Constants
from ..common.enums import ExecutionMode

class LiveTrader:
    def __init__(self, config, fyers, strategy:StrategyBase=None):
        self.fyers: fyersModel.FyersModel = fyers
        self.config = config
        self.instance_name = ""
        self.symbol = ""
        self.lot_size = ""
        self.interval = 0  # integer format as 1,5,240,1440
        self.strategy = strategy
        self.candles = []
        self.active_position = None
        self.current_position = 0
        self.pending_order_qty = 0
        self.is_started = False
        self.backtest_current_time = None
        self.market_open_time = None
        self.market_close_time = None
        self.start_time = None
        self.end_time = None

    def on_data(self, df):
        if self.is_started is False:
            return
        
        signal = self.strategy.process(df)
        if Constants.EXECTION_MODE == ExecutionMode.BACKTEST:
            self.on_backtest_signal(signal)
        else:
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
        if Constants.EXECTION_MODE is not ExecutionMode.LIVE:
            return

        # Current time with microseconds
        now_time = datetime.now().time()

        # if the signal is generated outside start time and end time, ignore it.
        if not (self.market_open_time <= now_time <= self.market_close_time):
            self.log(f"MARKET IS CLOSED, NEED TO SEND ORDER OF {order_qty} WHEN MARKET OPENS NEXT TIME.")
            self.save_state(order_qty)
            self.log(f"When you will start the application next working day, this will automatically execute the pending order IF STATE IS SAVED.")
            return
        
        # if the signal is generated after market is closed we need to retry
        if not (self.start_time <= now_time <= self.end_time):
            self.log(f"Ignoring the signal because it is generated outside start and end time")
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
            "orderTag": f"{self.instance_name}_FYERS_API"
        }
        response = self.fyers.place_order(order)
        
        if response.get("s") == "ok":
            self.log(f"Market order {response.get("id")} sent successfully, assuming filled!")
            self.current_position = order_qty
        else:
            # TODO: Retry order if sending is failed
            self.log_error(f"Order sending failed {response}")
            
    def get_safe_range_ending_last_closed_candle(self, now, interval_minutes: int):
        # Step 1: Avoid landing exactly at the next candle's open time
        
        if Constants.EXECTION_MODE == ExecutionMode.LIVE or now is None:
            now = datetime.now()
                    
        # now = datetime.now()
        adjusted_now = now - timedelta(seconds=1)

        # Step 2: Align to the most recent fully closed candle
        minute_bucket = (adjusted_now.minute // interval_minutes) * interval_minutes
        end = adjusted_now.replace(minute=minute_bucket, second=0, microsecond=0)

        if end > adjusted_now:
            end -= timedelta(minutes=interval_minutes)
            
        start = end - timedelta(days=self.strategy.required_ohlc_length)

        # Step 4: Convert to UNIX timestamps
        return int(start.timestamp()), int(end.timestamp())

            
    def run(self, curr_time = None):
        
        if self.pending_order_qty is not 0:
            self.place_order(self.pending_order_qty)
            return

        # simulated_date_str="12-06-2025"
        # simulated_time_str="09:15"
        # curr_time = datetime.strptime(f"{simulated_date_str} {simulated_time_str}", "%d-%m-%Y %H:%M")
        range_from, range_to = self.get_safe_range_ending_last_closed_candle(curr_time, interval_minutes=self.interval)
    
        params = {
            "symbol": self.symbol,
            "resolution": self.convertIntervalToFyersType(self.interval),
            "date_format": "0",
            "range_from": range_from,
            "range_to": range_to,
            "cont_flag": "1"
        }

        data = self.fyers.history(params)
        if "candles" not in data or not data["candles"]:
            self.log_error(f"Did not receive ohlc data. {data} | Skipping this run.")
            return
        
        df = pd.DataFrame(data['candles'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata')

        self.on_data(df)
        
        now_time = datetime.now().time()
        # check if this is the last run, if so, do cleanup and save state.
        if not (now_time <= self.market_close_time):
            self.save_state()
            self.log("::::: STRATEGY COMPLETED FOR TODAY, PLEASE RESTART NEXT WORKING DAY :::::")
            import os
            import signal
            os.kill(os.getpid(), signal.SIGINT)
        
    def save_state(self, pending_order_qty=0):
        data = {
            "current_position": self.current_position
        }
        if pending_order_qty is not 0:
            data["pending_order_action"] = {
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "order_qty": pending_order_qty
            }
            
        self.log(FileUtility.updateJsonObjectFile("./state.json", self.instance_name, data )["log"])
        
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
                if "current_position" in saved_state[self.instance_name]:
                    self.current_position = saved_state[self.instance_name]["current_position"] or 0
                    
                if "pending_order_action" in saved_state[self.instance_name]:
                    self.pending_order_qty = saved_state[self.instance_name]["order_qty"] or 0
                self.log(f"Successfully loaded the current position as {self.current_position} and pending order qty as {self.pending_order_qty}")
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
    
    def on_backtest_signal(self, signal: StrategySignal):
        # The current time will be the action time not the candle's time with which the signal is generated.
        self.log(f"Action: {signal} | Action Candle: {self.backtest_current_time}")
    
    def backtest_loop(self, days: int):
        """
        Run the backtest loop for the given number of days and time interval.
        """
        end_time = datetime.now()
        
        # Get the date `days` ago and set time to 0
        # 9:15
        start_date = (end_time - timedelta(days=days)).date()
        start_time = datetime.combine(start_date, time(9, 15))  # backtesting always starts from 9:15 AM
        
        self.log(f"Backtest period: {start_time.strftime("%Y-%m-%d %H:%M:%S")} to {end_time.strftime("%Y-%m-%d %H:%M:%S")}")
        
        market_open = time(self.config["start_time"][0],self.config["start_time"][1])
        market_close = time(self.config["end_time"][0],self.config["end_time"][1])
        
        self.log(f"Market hours: {market_open.strftime("%Y-%m-%d %H:%M:%S")} to {market_close.strftime("%Y-%m-%d %H:%M:%S")}")
        
        self.backtest_current_time = start_time
        while self.backtest_current_time <= end_time:
            if market_open <= self.backtest_current_time.time() <= market_close:
                self.run(self.backtest_current_time)
                time_module.sleep(0.1)
                
            self.backtest_current_time += timedelta(minutes=self.interval)
            
        self.log("Backtesting completing, shutting down")
            
        import os
        import signal
        os.kill(os.getpid(), signal.SIGINT)        

    def start(self):
        self.log("Starting Live Trader")
        
        if not self.load_config():
            return
        
        if not self.validate():
            self.log("Validation failed. Stoping Live Trader")
            return
        
        self.is_started = True
        
        self.log("Trade Engine Started")
        
        if Constants.EXECTION_MODE == ExecutionMode.LIVE:
            self.load_saved_state()
        
            action_scheduler_params = ActionSchedulerParams(
                start_time=self.market_open_time, 
                end_time=self.market_close_time, 
                interval=self.config["interval"]
                )
            action_scheduler = ActionScheduler(action_scheduler_params)
            action_scheduler.schedule(self.run)
            
        elif Constants.EXECTION_MODE == ExecutionMode.BACKTEST:
            self.backtest_loop(Constants.BACKTESTING_PERIOD)
            pass

        
    def validate(self) -> bool:
        if self.strategy is None:
            self.log_error("No strategy object provided to live trader")
            return False
        
        if not self.strategy.is_valid:
            self.log_error("Strategy object provided to live trader found invalid")
            return False
        
        try:
            self.market_open_time = time(self.config["market_open_time"][0],self.config["market_open_time"][1])
            self.market_close_time = time(self.config["market_close_time"][0],self.config["market_close_time"][1])
            
            self.start_time = time(self.config["start_time"][0],self.config["start_time"][1])
            self.end_time = time(self.config["end_time"][0],self.config["end_time"][1])
        except Exception as e:
            self.log_error(f"Error setting up market timings: {e}")
            return False
        
        return True
    
    def convertIntervalToFyersType(self, interval: int) -> str:
        if interval == 1440:
            return "1D"
        return interval
    
    def log(self, content):
        Logger.log(f"LiveTrader::{self.instance_name}:: {content}")
        
    def log_error(self, content):
        Logger.error(f"LiveTrader::{self.instance_name}:: {content}")