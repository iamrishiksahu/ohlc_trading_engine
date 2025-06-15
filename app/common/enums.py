from enum import Enum

class ExecutionMode(Enum):
    LIVE="LIVE",
    BACKTEST="BACKTEST"

class StrategySignal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"
    
class LogType(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"