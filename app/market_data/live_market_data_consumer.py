from abc import abstractmethod

class LiveMarketDataConsumer():
    def __init__(self):
        pass
    
    @abstractmethod
    def on_tick(self, symbol: str, data: dict) -> None:
        """
        Called on receiving live market data
        Optionally latency measurement can be perfrormed here.
        If want to do any processing here, call the super().on_tick() at the end of the function
        otherwise this can hamper performance
        
        """

    def on_subscription_failure(self, symbol: str) -> None:
        pass
    
    def on_subscription_success(self, symbol: str) -> None:
        pass