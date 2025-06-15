import asyncio
import signal
import win32api
import win32con
import argparse
import sys
from app.Main import Main
from .utils.Constants import Constants
from .common.enums import ExecutionMode

def get_cli_args():
    parser = argparse.ArgumentParser()
    
    # Flags
    parser.add_argument("--run", action="store_true", help="Run the live scheduler")
    parser.add_argument("--backtest", action="store_true", help="Run in backtest mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    # Conditional argument (optional, but required if --backtest is used)
    parser.add_argument("--period", type=int, help="Backtest period in days")

    args = parser.parse_args()

    # Enforce logic: if --backtest is set, then --period must be provided
    if args.backtest and args.period is None:
        parser.error("--period is required when using --backtest")
        raise Exception("--period is required when using --backtest")

    return args

async def start():
    
    # Parse CLI arguments to know whether to start in live or in backtest mode
    args = get_cli_args()
    
    if args.debug:
        print("Debug mode enabled")

    if args.backtest:
        Constants.EXECTION_MODE = ExecutionMode.BACKTEST
        Constants.BACKTESTING_PERIOD = args.period
        print(f"Running backtest for period: {args.period} days")

    app = Main()
    await app.start()

    # Run forever until interrupted
    stop_event = asyncio.Event()
    
    def shutdown(signum, frame):
        print(f"Received signal: {signum} => Shutting down...")
        asyncio.create_task(app.stop())
        stop_event.set()
        
    def windows_control_handler(ctrl_type):
        if ctrl_type == win32con.CTRL_CLOSE_EVENT or ctrl_type == win32con.CTRL_LOGOFF_EVENT or ctrl_type == win32con.CTRL_SHUTDOWN_EVENT:
            shutdown(f"Windows control event {ctrl_type}")

    win32api.SetConsoleCtrlHandler(windows_control_handler, True)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    await stop_event.wait()
