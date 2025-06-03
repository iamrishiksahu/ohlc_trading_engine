import asyncio
import signal
from .Main import Main

async def main():
    app = Main()
    await app.start()

    # Run forever until interrupted
    stop_event = asyncio.Event()

    def shutdown(signum, frame):
        print(f"Received signal: {signum} => Shutting down...")
        asyncio.create_task(app.stop())
        stop_event.set()

    loop = asyncio.get_running_loop()
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    await stop_event.wait()

if __name__ == "__main__":
    asyncio.run(main())
