from fyers_apiv3.FyersWebsocket import data_ws
from live_market_data_adapter import LiveMarketDataAdapter
import globals
            
class FyersMarketDataAdapter(LiveMarketDataAdapter):
    def __init__(self, fyers_instance):
        self.fyers: data_ws.FyersDataSocket = data_ws.FyersDataSocket(
            access_token=globals.config["fyers_access_token"],       # Access token in the format "appid:accesstoken"
            log_path="",                     # Path to save logs. Leave empty to auto-create logs in the current directory.
            litemode=False,                  # Lite mode disabled. Set to True if you want a lite response.
            write_to_file=False,              # Save response in a log file instead of printing it.
            reconnect=True,                  # Enable auto-reconnection to WebSocket on disconnection.
            on_connect=self.onopen,               # Callback function to subscribe to data upon connection.
            on_close=self.onclose,                # Callback function to handle WebSocket connection close events.
            on_error=self.onerror,                # Callback function to handle WebSocket errors.
            on_message=self.onmessage             # Callback function to handle incoming messages from the WebSocket.
        )

        # Establish a connection to the Fyers WebSocket
        self.fyers.connect()

    def subscribe(self, symbol, handler):
        self.fyers.subscribe(symbols=[symbol], data_type=self.get_data_type(symbol))
        self.subscribe_callback(symbol, handler)
    
    def unsubscribe(self, symbol, handler):
        self.fyers.unsubscribe(symbols=[symbol], data_type=self.get_data_type(symbol))
        self.unsubscribe_callback(symbol, handler)
        

    def onmessage(self, message):
        """
        Callback function to handle incoming messages from the FyersDataSocket WebSocket.

        Parameters:
            message (dict): The received message from the WebSocket.

        """
        print("Response:", message)
        if "symbol" not in message:
            return
        
        self.on_tick_callback(message["symbol"], message)


    def onerror(self, message):
        """
        Callback function to handle WebSocket errors.

        Parameters:
            message (dict): The error message received from the WebSocket.


        """
        
        print("Error:", message)


    def onclose(self, message):
        """
        Callback function to handle WebSocket connection close events.
        """
        self.is_ready = False
        print("Connection closed:", message)


    def onopen(self, ):
        """
        Callback function to subscribe to data type and symbols upon WebSocket connection.

        """
        self.is_ready = True
       

        # Keep the socket running to receive real-time data
        self.fyers.keep_running()
        
    def get_data_type(self, symbol: str) -> str:
        if "index" in symbol.lower():
            return "IndexUpdate"
        return "SymbolUpdate"
    


    # Create a FyersDataSocket instance with the provided parameters
    
    #  ------------------------------------------------------------------------------------------------------------------------------------------
    #  Sample Success Response 
    #  ------------------------------------------------------------------------------------------------------------------------------------------
            
    #   {
    #     "ltp":606.4,
    #     "vol_traded_today":3045212,
    #     "last_traded_time":1690953622,
    #     "exch_feed_time":1690953622,
    #     "bid_size":2081,
    #     "ask_size":903,
    #     "bid_price":606.4,
    #     "ask_price":606.45,
    #     "last_traded_qty":5,
    #     "tot_buy_qty":749960,
    #     "tot_sell_qty":1092063,
    #     "avg_trade_price":608.2,
    #     "low_price":605.85,
    #     "high_price":610.5,
    #     "open_price":609.85,
    #     "prev_close_price":620.2,
    #     "type":"sf",
    #     "symbol":"NSE:SBIN-EQ",
    #     "ch":-13.8,
    #     "chp":-2.23
    #   }
