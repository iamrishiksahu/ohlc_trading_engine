from live_market_data_consumer import LiveMarketDataConsumer
from live_market_data_adapter import LiveMarketDataAdapter
from market_data_adapter_factory import MarketDataAdapterFactory
from ..common.enums import BrokerType

class LiveMarketDataHandler():
    def __init__(self):
        self.symbol_vs_last_feed: dict[str, dict]
        self.market_data_consumer: LiveMarketDataConsumer = None
        self.broker_type: BrokerType = None
        self.market_data_adapter: LiveMarketDataAdapter = None
        
    def init(self, broker_instance,  broker_type: BrokerType, consumer: LiveMarketDataConsumer):
        self.market_data_consumer = consumer
        self.broker_type = broker_type
        self.market_data_adapter = MarketDataAdapterFactory.getAdapter(broker_instance, broker_instance)
            
    def subcribe(self, symbol: str) -> bool:
        self.market_data_adapter.subscribe(symbol, self)
    
    def unsubscribe(self, symbol: str, consumer: LiveMarketDataConsumer) -> bool:
        self.market_data_adapter.unsubscribe(symbol, self)
            
    def on_subscription_success(self, symbol: str) -> None:
        self.market_data_consumer.on_subscription_success(symbol)
        
    def on_subscription_failure(self, symbol: str) -> None:
        self.market_data_consumer.on_subscription_failure(symbol)
        
    def on_tick(self, symbol: str, data: dict) -> bool:
        self.symbol_vs_last_feed[symbol] = data
        self.market_data_consumer.on_tick(symbol, data)
    
    