from ..common.enums import BrokerType
from live_market_data_adapter import LiveMarketDataAdapter
from fyers_market_data_adapter import FyersMarketDataAdapter

class MarketDataAdapterFactory:
    """ Helps maintain a single market data adapter for a single broker """
    _instances = {}

    @classmethod
    def getAdapter(cls, broker_instance, broker_type: BrokerType) -> LiveMarketDataAdapter:
        if broker_type not in cls._instances:
            if broker_type == BrokerType.FYERS:
                cls._instances[broker_type] = FyersMarketDataAdapter(broker_instance)
            else:
                raise ValueError(f"Unsupported broker type: {broker_type} for market data")
        return cls._instances[broker_type]
