from abc import abstractmethod
from ..common.enums import StrategySignal
    
class StrategyBase:
    
    def __init__(self):
        self.is_valid = False
        self.required_ohlc_length = 1
    @abstractmethod
    def process(self, df) -> StrategySignal:
        """Runs strategy logic and returns signals."""
        pass
    
    @abstractmethod
    def validate(self, strategy_params) -> bool:
        """Validates strategy parameters."""
        pass
    