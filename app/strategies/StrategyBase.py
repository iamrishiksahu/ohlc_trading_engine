from abc import abstractmethod
from enum import Enum

class StrategySignal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"
    
class StrategyBase:
    
    def __init__(self):
        self.is_valid = False
        
    @abstractmethod
    def process(self, df) -> StrategySignal:
        """Runs strategy logic and returns signals."""
        pass
    
    @abstractmethod
    def validate(self, strategy_params) -> bool:
        """Validates strategy parameters."""
        pass
    