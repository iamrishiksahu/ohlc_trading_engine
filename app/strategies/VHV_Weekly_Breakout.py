import pandas as pd
from dataclasses import dataclass
from ..utils.Logger import Logger
from .StrategyBase import StrategyBase
from ..common.enums import StrategySignal, Side
from decimal import Decimal
from datetime import datetime, time

@dataclass
class WeeklyHigh:
    value: Decimal
    last_updated: datetime = datetime.now()

@dataclass
class VHV_Weekly_Breakout_Params:
    breakout_period: int
    max_stocks_to_execute: float

@dataclass
class Position:
    symbol: str
    side: Side
    is_closed: False
    sl_price: Decimal
    closed_at: datetime
    opened_at: datetime = datetime.now()
    entry_quantity: int = 0
    exit_quantity: int = 0
    avg_entry_price: Decimal = 0
    avg_exit_price: Decimal = 0

class VHV_Weekly_Breakout(StrategyBase):
    def __init__(self, params: VHV_Weekly_Breakout_Params, interval: int):
        self.strategy_params = params
        self.is_valid = False
        self.interval = interval
        self.weekly_window_highs: dict[str, WeeklyHigh] = {}
        self.candles: dict[str, pd.DataFrame] = {}
        self.ongoing_positions: dict[str, Position] = {}
        self.closed_positions: dict[str, list[Position]] = {}
        
    def process_ohlc(self, df: pd.DataFrame, script_name: str) -> tuple[StrategySignal, str]:
        # This is an ohlc update of a particular script
        # extract the high of the window
        self.candles[script_name] = df
        self.weekly_window_highs[script_name] = WeeklyHigh(value=df['high'].max(), last_updated=datetime.now()) 
        
        if script_name in self.ongoing_positions:
            # TODO: Calculate trailing SL
            pass
        return StrategySignal.NONE, script_name

        
    def process_tick(self, data: dict, script_name: str) -> tuple[StrategySignal, str]:

        if script_name in self.ongoing_positions:
            position = self.ongoing_positions[script_name]
            # TODO: calculate the new trailing SL and modify the sl order
                
        
        # new position should only be taken between 3:15 PM to 3:30 PM
        if time(15, 15) <= datetime.now().time() <= time(15,30):
            if script_name in self.weekly_window_highs and self.weekly_window_highs[script_name] < data["ltp"]:
                # weekly high broken.
                return StrategySignal.BUY, script_name
                               
        return StrategySignal.NONE, script_name
    
    def on_trade(self, symbol: str, qty, price: Decimal, side: Side) -> None:
        if symbol not in self.ongoing_positions:
            self.ongoing_positions = Position(side=side, quantity=qty, symbol=symbol, avg_entry_price=price)
            return
        
        if side == self.ongoing_positions[symbol].side:
            # position addition
            self.ongoing_positions[symbol].avg_entry_price = (self.ongoing_positions[symbol].avg_entry_price * self.ongoing_positions[symbol].entry_quantity + price * qty) / (self.ongoing_positions[symbol].entry_quantity + qty)
            self.ongoing_positions[symbol].entry_quantity += qty
        else:
            # position close
            self.ongoing_positions[symbol].avg_exit_price = (self.ongoing_positions[symbol].avg_exit_price * self.ongoing_positions[symbol].exit_quantity + price * qty) / (self.ongoing_positions[symbol].exit_quantity + qty)
            self.ongoing_positions[symbol].exit_quantity += qty
            
        if self.ongoing_positions[symbol].entry_quantity != 0 and self.ongoing_positions[symbol].entry_quantity == self.ongoing_positions[symbol].exit_quantity:
            self.close_position(self.ongoing_positions[symbol])
        
        return super().on_trade(symbol, qty, side)
    
    def close_position(self, position: Position) -> None:
        del self.ongoing_positions[position.symbol]
        position.is_closed = True
        position.closed_at = datetime.now()
        if position.symbol not in self.closed_positions:
            self.closed_positions[position.symbol] = []
        self.closed_positions[position.symbol].append(position)
    
    def init(self) -> bool:
        self.symbols_to_subscribe_live_feed = [symbol.symbol for symbol in self.symbols]
        self.weekly_window_highs = {symbol.symbol: 10**8 for symbol in self.symbols}
        return self.validate(self.strategy_params)
    
    def validate(self, strategy_params: VHV_Weekly_Breakout_Params) -> bool:
        if not isinstance(strategy_params.breakout_period, int):
            Logger.error("breakout_period must be an integer")
            return False
        if not isinstance(strategy_params.max_stocks_to_execute, (int, float)):
            Logger.error("max_stocks_to_execute must be a number")
            return False
        
        self.is_valid = True
        self.required_ohlc_length = max(self.strategy_params.atr_period / 10 * self.interval / 2, 1)
        Logger.log(f"required_ohlc_length: {self.required_ohlc_length}")
        Logger.log("Strategy validated successfully") 
        return True