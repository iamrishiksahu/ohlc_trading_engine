from fyers_apiv3 import fyersModel
from datetime import datetime
import json
from datetime import datetime, timedelta
import time
from .utils.MainUtil import MainUtil
from .utils.Constants import Constants
import re


class HistoricalDataDownloader:
    
    def __init__(self, broker):
        self.__broker_instance = broker
        self.scripts: list = []
        self.cache = []

    def perform(self, frmdt: str, todt: str, scrpt: str, timeframe: str="1D"):
        fromDatestr: str = frmdt
        toDatestr: str = todt
        fromDateObj: datetime = datetime.strptime(fromDatestr, "%Y-%m-%d")
        toDateObj: datetime = datetime.strptime(toDatestr, "%Y-%m-%d")

        # Convert to Unix timestamp
        fromTimestamp: str = str(int(fromDateObj.timestamp()))
        toTimestamp: str = str(int(toDateObj.timestamp()))


        data: dict = {
            "symbol": scrpt,
            "resolution": timeframe,
            "date_format":"0",
            "range_from":fromTimestamp,
            "range_to":toTimestamp,
            "cont_flag":"1"
        }

        response = self.__broker_instance.history(data=data)
        
        # return print(response)

        if 'code' in response and response['code'] != 200:
            # Some error occurred
            print(response)
    

        histData: list = response['candles']

        # Convert data into string
        newHistData = ""
        for item in histData:
            date = datetime.fromtimestamp(int(item[0])).strftime('%Y-%m-%d %H:%M')
            item[0] = date
            newHistData += ",".join([str(a) for a in item]) + "\n"
            
        return newHistData

    def setScripts(self, scripts: list):
        self.scripts = scripts

    def downloadData(self, startDate: str, endDate: str, timeframe: str = "1D"):
        for script in self.scripts:
            fromDt = startDate
            toDt = self.get_date_after_n_days(fromDt, 99)
            if toDt > endDate : toDt = endDate
            filename = script.replace(":","-") + "(" + timeframe + ") [" + f"{startDate} -  {self.get_date_after_n_days(endDate, -1)}" + "].csv"
            print("CURRENT: " + script)
            data = ""
            
            while toDt <= endDate and fromDt <= toDt:
                print(fromDt + "  " + toDt )  
                data += self.perform(fromDt, toDt, script, timeframe)
                time.sleep(2)
                    
                fromDt = self.get_date_after_n_days(toDt, 1)
                toDt = self.get_date_after_n_days(fromDt,99) 
                if toDt > endDate : toDt = endDate                      

            
            MainUtil.writeFile(Constants.DIR_HISTORICAL_DATA.joinpath(filename), data)
        
    def get_date_after_n_days(self, date_str: str, n: int):

        # Convert the input string to a datetime object
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Add n days using timedelta
        new_date = date_obj + timedelta(days=n)
        
        # Return the resulting date as a string in the same format
        return new_date.strftime("%Y-%m-%d")

    def downloadStrategy(self, strategyStr: str, startDate: str, endDate: str, timeframe: str = "1D"):
        if self.is_valid_strategy_expression(strategyStr) is not True:
            return
        
        groups = self.extract_scripts_and_multipliers(strategyStr)
        # for multiplier, symbol in groups:
            
            
    
    def is_valid_strategy_expression(self, s: str) -> bool:
        pattern = re.compile(r"""
            ^                                                   # Start
            [+-]?                                               # Optional + or -
            (?:
                \d+\*                                           # Optional multiplier
            )?
            [A-Z]+:                                             # Exchange (e.g. NSE)
            (?:
                [A-Z]+[0-9]+[A-Z]+                              # Format 1
                |
                [A-Z]+-[A-Z]+                                   # Format 2
            )
            (                                                   # Repeating group
                [+-]
                (?:
                    \d+\*
                )?
                [A-Z]+:
                (?:
                    [A-Z]+[0-9]+[A-Z]+
                    |
                    [A-Z]+-[A-Z]+
                )
            )*
            $                                                   # End
        """, re.VERBOSE)

        return bool(pattern.match(s))

    def extract_scripts_and_multipliers(self, s: str):
        # Ensure the first term starts with '+' or '-' for uniform parsing
        if not s.startswith(('+', '-')):
            s = '+' + s

        # Regex pattern for the two valid formats
        token_pattern = re.compile(r'''
            ([+-])                        # 1. Sign
            (?:(\d+)\*)?                  # 2. Optional multiplier
            ([A-Z]+:                      # 3. Exchange:
            (?:
                [A-Z]+[0-9]+[A-Z]+        #    Format 1: SYMBOL + DIGITS + SUFFIX
                |
                [A-Z]+-[A-Z]+             #    Format 2: SYMBOL-SUFFIX
            ))
        ''', re.VERBOSE)

        groups = []
        for sign, multiplier, symbol in token_pattern.findall(s):
            mult = int(multiplier) if multiplier else 1
            if sign == '-':
                mult *= -1
            groups.append((mult, symbol))

        return groups

            