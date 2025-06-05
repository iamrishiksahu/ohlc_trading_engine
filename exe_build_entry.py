import asyncio
import signal
import win32api
import win32con
from app.Main import Main

async def main():
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

if __name__ == "__main__":
    asyncio.run(main())
