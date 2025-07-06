from abc import abstractmethod
from live_market_data_handler import LiveMarketDataHandler
from datetime import datetime

class LiveMarketDataAdapter():
    def __init__(self):
        self.symbol_vs_market_data_handler: dict[str, set[LiveMarketDataHandler]] = {}
        self.symbol_vs_last_received: dict[str, datetime] = {}
        self.is_ready = False
        
    @abstractmethod
    def on_tick(self, symbol:str, data: dict) -> None:
        """processes market data"""
    
    @abstractmethod
    def subscribe(self, symbol: str, handler: LiveMarketDataHandler):
        """subscribes market data"""
        
    @abstractmethod
    def unsubscribe(self, symbol: str, handler: LiveMarketDataHandler):
        """subscribes market data"""
    
    @abstractmethod
    def on_subscription_success(self, symbol: str):
        """ handles successful subscription """
        
    @abstractmethod
    def on_subscription_failure(self, symbol: str):
        """ handles failed subscription """
        
    def subscribe_callback(self, symbol: str, handler: LiveMarketDataHandler):
        if symbol not in self.symbol_vs_market_data_handler:
            self.symbol_vs_market_data_handler[symbol] = []
            
        self.symbol_vs_market_data_handler[symbol].add(handler)
        
    def unsubscribe_callback(self, symbol: str, handler: LiveMarketDataHandler):
        if symbol not in self.symbol_vs_market_data_handler:
            return
        self.symbol_vs_market_data_handler[symbol].remove(handler)
    
    def on_subscription_success_callback(self, symbol: str):
        for _handler in self.symbol_vs_market_data_handler[symbol]:
            _handler.on_subscription_success(symbol)
        
    def on_subscription_failure_callback(self, symbol: str):
        for _handler in self.symbol_vs_market_data_handler[symbol]:
            _handler.on_subscription_success(symbol)
            
    def on_tick_callback(self, symbol:str, data: dict) -> None:
        if symbol not in self.symbol_vs_market_data_handler:
            return
        for handler in self.symbol_vs_market_data_handler[symbol]:
            handler.on_tick(symbol, data)