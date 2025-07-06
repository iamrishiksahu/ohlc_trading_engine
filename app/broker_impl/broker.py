from ..common.enums import BrokerType

class Broker:
    _instance = None
    _broker_type: BrokerType = None

    def __init__(self, broker_type: BrokerType):
        if Broker._instance is not None:
            raise Exception("Broker is a singleton. Use Broker.GetInstance().")

        self._broker_type = broker_type
        print(f"Initializing broker with type {broker_type}")
        Broker._instance = self

    @classmethod
    def GetInstance(cls, broker_type: BrokerType = None):
        if cls._instance is None:
            if broker_type is None:
                raise Exception("Broker must be initialized with broker_type first.")
            cls._instance = cls(broker_type)
        else:
            if broker_type is not None and broker_type != cls._instance._broker_type:
                raise Exception(f"Broker already initialized with {cls._instance._broker_type}, not {broker_type}")
        return cls._instance
