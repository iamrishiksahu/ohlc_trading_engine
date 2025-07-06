from abc import abstractmethod
from ..common.enums import StrategySignal, Side
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
from decimal import Decimal

@dataclass
class Symbol:
    symbol: str
    interval: int # in minutes
    required_ohlc_length: int = 1 # this will be by default set equal to  interval.
    last_ohlc_fetched_at: datetime = datetime.fromtimestamp(0)
    fetch_ohlc_next_at: datetime = datetime.fromtimestamp(0)
    
    def __post_init__(self):
        self.required_ohlc_length = self.interval

class StrategyBase:
    
    def __init__(self):
        self.is_valid: bool = False
        self.symbols: list[Symbol] = []
        self.symbols_to_subscribe_live_feed: list[str] = []
                
    @abstractmethod
    def init(self) -> bool:
        """Initializes the strategy parameters and does first time jobs"""
        return True
    
    @abstractmethod
    def validate(self, strategy_params) -> bool:
        """Validates strategy parameters."""
        pass

    def process_ohlc(self, df: pd.DataFrame, script_name: str) -> tuple[StrategySignal, str]:
        """Runs strategy logic and returns signals."""
        return StrategySignal.NONE, script_name
    
    def process_tick(self, data: dict, script_name: str) -> tuple[StrategySignal, str]:
        """Runs strategy logic and returns signals."""
        return StrategySignal.NONE, script_name
    
    def on_trade(self, symbol: str, qty: int, price: Decimal, side: Side):
        """Callback on trade"""
    

    