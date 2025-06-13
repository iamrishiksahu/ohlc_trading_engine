import requests
import pyotp
import json
import threading
import webbrowser
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from fyers_apiv3 import fyersModel
from .utils.Logger import Logger
from .HistoricalDataDownloader import HistoricalDataDownloader
from .live.trader import LiveTrader
from .strategies.SB_VOL import StrategySBVOL, SBVolParams

class Main:
    
    def __init__(self):
        
        self.fyers = None

        # User credentials
        self.client_id = """"  # e.g., 'AB1234'
        self.app_id = """"  # e.g., 'AB1234-100'
        self.app_secret = """"
        self.redirect_uri = """"

        # Config
        self.token_dir = "./data/tokens"
        self.token_path = os.path.join(self.token_dir, "access_token.json")

        # Global variable to store the authorization code
        self.auth_code = None
        self.fyers = None

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
            session = fyersModel.SessionModel(
                client_id=self.app_id,
                secret_key=self.app_secret,
                redirect_uri=self.redirect_uri,
                response_type="code",
                grant_type="authorization_code"
            )
            auth_code_url = session.generate_authcode()

            # === Start local server to capture auth_code ===
            auth_context = {"auth_code": None}
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
            token_data = session.generate_token()
            access_token = token_data.get("access_token")

            if not access_token:
                raise Exception("❌ Failed to generate access token.")

            # Save token
            with open(self.token_path, "w") as f:
                json.dump(token_data, f)
            Logger.log("✅ Token saved to", self.token_path)

            # Create global fyers instance
            self.fyers = fyersModel.FyersModel(client_id=self.app_id, token=access_token, log_path="")

    async def start(self):
        Logger.init()
        self.authenticate()
        profile = self.fyers.get_profile()
        Logger.log(profile)
        
        hdl = HistoricalDataDownloader(self.fyers)
        strategy_params: SBVolParams = SBVolParams(atr_period=10, multiplier=3, use_true_atr=True)
        strategy = StrategySBVOL(strategy_params)
        live_trader = LiveTrader(self.fyers, lot_size=1, symbol="NSE:RELIANCE-EQ", interval=30, strategy=strategy)
        live_trader.start()
        # Get the exact script name from the fyers web app.
        hdl.setScripts([
               "NSE:RELIANCE-EQ",
            # Add more if you want
        ])
        
        # Dates has to be entered in YYYY-MM-DD format only
        startDate = "2025-06-01" 
        endDate = "2025-06-14"
        timeframe = "15"
        
        hdl.downloadData(startDate, endDate, timeframe)
        
        
    async def stop(self):
        await Logger.shutdown()
        
        

            



    