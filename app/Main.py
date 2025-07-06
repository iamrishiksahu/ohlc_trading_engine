import requests
import pyotp
import json
import threading
import webbrowser
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from fyers_apiv3 import fyersModel
from .utils.Logger import Logger
from .utils.FileUtility import FileUtility
from .HistoricalDataDownloader import HistoricalDataDownloader
from .live.trader import LiveTrader
from .strategies.SB_VOL import StrategySBVOL, SBVolParams

class Main:
    
    def __init__(self):
        
        self.fyers: fyersModel.FyersModel = None

        # User credentials
        self.client_id: str = ""  # e.g., 'AB1234'
        self.app_id: str = ""  # e.g., 'AB1234-100'
        self.app_secret: str = ""
        self.redirect_uri: str = ""
        
        self.trading_configs: json = []
        self.live_trader_instances: list[LiveTrader] = []

        # Config
        self.token_dir = "./data/tokens"
        self.token_path = os.path.join(self.token_dir, "access_token.json")

        # Global variable to store the authorization code
        self.auth_code = None

    # === Check if token already exists and is valid ===
    def load_valid_token(self):
        if not os.path.exists(self.token_path):
            return None
        try:
            with open(self.token_path, "r") as f:
                token_data = json.load(f)
            access_token = token_data.get("access_token")
            if not access_token:
                return None

            test_fyers = fyersModel.FyersModel(client_id=self.app_id, token=access_token, log_path="")
            profile = test_fyers.get_profile()
            if profile.get("s") == "ok":
                Logger.log("✅ Reusing existing valid token.")
                self.fyers = test_fyers  # ⬅️ Set global fyers instance
                return access_token
            else:
                Logger.log("⚠️ Token invalid or expired, re-authenticating...")
                return None
        except Exception as e:
            Logger.log("⚠️ Failed to validate token:", e)
            return None
        
    def authenticate(self):
        os.makedirs(self.token_dir, exist_ok=True)

        access_token = self.load_valid_token()
        if not access_token:
            session: fyersModel.SessionModel = fyersModel.SessionModel(
                client_id=self.app_id,
                secret_key=self.app_secret,
                redirect_uri=self.redirect_uri,
                response_type="code",
                grant_type="authorization_code"
            )
            auth_code_url = session.generate_authcode()

            # === Start local server to capture auth_code ===
            auth_context: dict = {"auth_code": None}
            class AuthCodeHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    from urllib import parse
                    qs = parse.parse_qs(parse.urlparse(self.path).query)
                    auth_context["auth_code"] = qs.get("auth_code", [None])[0]
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"<h1>Authorization successful!</h1><p>You can close this tab now.</p>")

            def start_server():
                HTTPServer(("localhost", 8080), AuthCodeHandler).handle_request()

            Logger.log("🌐 Opening browser for authorization...")
            threading.Thread(target=start_server).start()
            webbrowser.open(auth_code_url)

            while not auth_context["auth_code"]:
                pass
            
            # Step 5: Get token
            session.set_token(auth_context["auth_code"])
            token_data: dict = session.generate_token()
            access_token = token_data.get("access_token")

            if not access_token:
                raise Exception("Failed to generate access token.")

            # save toke in global context
            
            import globals
            globals.config["fyers_access_token"] = access_token
            
            # Save token in file
            with open(self.token_path, "w") as f:
                json.dump(token_data, f)
            Logger.log("✅ Token saved to", self.token_path)

            # Create global fyers instance
            self.fyers = fyersModel.FyersModel(client_id=self.app_id, token=access_token, log_path="")

    def load_config(self) -> bool:
        
        if FileUtility.checkIfFileExists("./config.json")["data"] is not True:
            Logger.error(f"Couldn't load config file. Shutting down.")
            return False
        
        file_data: dict[str, str] = FileUtility.readFile("./config.json")["data"]
        
        try:
            json_data: json = json.loads(file_data)
            fyers_config = json_data["fyers"]
            
            self.app_id = fyers_config["app_id"]
            self.app_secret = fyers_config["app_secret"]
            self.client_id = fyers_config["client_id"]
            self.redirect_uri = fyers_config["redirect_uri"]
            
            trading_config: json = json_data["trading"]
            for t_cfg in trading_config:
                if t_cfg["enabled"]:
                    t_cfg["start_time"] = [int(part) for part in t_cfg["start_time"].split(":")]
                    t_cfg["end_time"] = [int(part) for part in t_cfg["end_time"].split(":")]
                    t_cfg["market_open_time"] = [int(part) for part in t_cfg["market_open_time"].split(":")]
                    t_cfg["market_close_time"] = [int(part) for part in t_cfg["market_close_time"].split(":")]
                    
                    self.trading_configs.append(t_cfg)
            
            Logger.log(self.trading_configs)
            
        except Exception as e:
            Logger.error(f"Error loading config: {e}")
            return False
        
        return True
        
    async def start(self):
        Logger.init()
        if not self.load_config():
            await self.stop()
            return
        
        self.authenticate()
        
        profile = self.fyers.get_profile()
        if profile.get("s") != "ok":
            Logger.log(profile)
            Logger.log("There is some problem connecting to fyers. Shutting down.")
            await self.stop()
            return
        
        Logger.log(profile)
        
        # hdl = HistoricalDataDownloader(self.fyers)
        # hdl.setScripts([
        #     "NSE:NIFTY50-INDEX"
        # ])
        # hdl.downloadData("2022-01-01", "2025-06-18", "30")
        
        
        # return
        
        for config in self.trading_configs:
            try:
                if config["strategy"] == "SB_VOL":
                    strategy_params: SBVolParams = SBVolParams(
                        atr_period=config["strategy_parameters"]["atr_period"], 
                        multiplier=config["strategy_parameters"]["multiplier"], 
                        use_true_atr=config["strategy_parameters"]["use_true_atr"])
                    strategy = StrategySBVOL(strategy_params, config["interval"])
                    
                    live_trader:LiveTrader = LiveTrader(config, self.fyers, strategy=strategy)
                    live_trader.start()
                    
                    self.live_trader_instances.append(live_trader)
                else:
                    Logger.log(f"Unknown strategy name provided for instance: {config["instance_name"]}")
                
            except Exception as e:
                Logger.error(f"Error loading strategy instance: {config["instance_name"]}. {e}") 

    async def stop(self):
        await Logger.shutdown()