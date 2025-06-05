import os
import asyncio
from datetime import datetime
from enum import Enum
from pathlib import Path
import threading
from .Constants import Constants
from .FileUtility import FileUtility


class LogType(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Logger:
    LOG_DIR = Constants.DIR_LOGS
    MAX_LOG_COUNT_PER_FILE = 1000

    _queue: asyncio.Queue = asyncio.Queue()
    _writer_task: asyncio.Task = None
    _log_filepath: Path = None
    _log_count: int = 0
    _current_log_count: int = 0
    _print_logs: bool = True
    _started: bool = False

    @classmethod
    def _ensure_log_dir(cls):
        os.makedirs(cls.LOG_DIR, exist_ok=True)

    @classmethod
    def _get_log_filename(cls):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H-%M-%S")
        suffix = f"_{cls._log_count // cls.MAX_LOG_COUNT_PER_FILE}" if cls._current_log_count >= cls.MAX_LOG_COUNT_PER_FILE else ""
        filename = f"{date_str}_{time_str}{suffix}.log"
        return cls.LOG_DIR / filename

    @classmethod
    async def _write_worker(cls):
        print("Logger worker started")
        while True:
            log_msg = await cls._queue.get()
            try:
                cls._current_log_count += 1
                cls._log_count += 1

                if cls._log_filepath is None or cls._current_log_count > cls.MAX_LOG_COUNT_PER_FILE:
                    cls._current_log_count = 1
                    cls._log_filepath = cls._get_log_filename()

                print(cls._log_filepath, log_msg)
                FileUtility.appendFile(cls._log_filepath, log_msg)
            except Exception as e:
                print(f"⚠️ Logger write failed: {e}")

    @classmethod
    def init(cls):
        if not cls._started:
            cls._ensure_log_dir()
            try:
                # Already in an async context
                loop = asyncio.get_running_loop()
                return asyncio.create_task(cls._write_worker())  # non-blocking
            except RuntimeError:
                # We're in a sync context, so run the shutdown safely
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                cls._writer_task = loop.create_task(cls._write_worker())
                threading.Thread(target=loop.run_forever, daemon=True).start()
            cls._started = True
            print("Logger started")
            
    @classmethod
    def error(clas, *args, type=LogType.ERROR, sep=" ", end="\n"):
        Logger.log(args, type, sep, end)
        
    @classmethod
    def critical(clas, *args, type=LogType.CRITICAL, sep=" ", end="\n"):
        Logger.log(args, type, sep, end)
        
    @classmethod
    def warning(clas, *args, type=LogType.WARNING, sep=" ", end="\n"):
        Logger.log(args, type, sep, end)

    @classmethod
    def log(cls, *args, type=LogType.INFO, sep=" ", end="\n"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        message = sep.join(str(arg) for arg in args)
        log_entry = {
            "timestamp": timestamp,
            "type": type.name,
            "message": message
        }
        
        formatted = str(log_entry) + end

        if cls._print_logs:
            print(log_entry, end="")

        try:
            # Are we in an active asyncio event loop? (i.e., async context)
            loop = asyncio.get_running_loop()
            # ✅ In async context → schedule task directly
            asyncio.create_task(cls._queue.put(formatted))
        except RuntimeError:
            # ❌ Not in async context → schedule safely from sync code
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(cls._queue.put_nowait, formatted)


    @classmethod
    async def shutdown(cls):
        async def _shutdown():
            await asyncio.sleep(0.5)  # Let queue flush
            if cls._writer_task:
                cls._writer_task.cancel()
                try:
                    await cls._writer_task
                    Logger.log("Logger shutdown success")
                except asyncio.CancelledError:
                    pass

        try:
            # Already in an async context
            loop = asyncio.get_running_loop()
            return asyncio.create_task(_shutdown())  # non-blocking
        except RuntimeError:
            # We're in a sync context, so run the shutdown safely
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_shutdown())
            loop.close()
