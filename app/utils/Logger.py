import os
import asyncio
from datetime import datetime
from enum import Enum
from pathlib import Path
import threading
from .Constants import Constants
from .FileUtility import FileUtility
from ..common.enums import LogType


class Logger:
    LOG_DIR = Constants.DIR_LOGS
    MAX_LOG_COUNT_PER_FILE = 3000

    _queue = asyncio.Queue()
    _log_filepath: Path = None
    _log_count = 0
    _current_log_count = 0
    _print_logs = True
    _started = False
    _loop = None

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
        return Path(cls.LOG_DIR) / filename

    @classmethod
    def _write_log(cls, data: str):
        try:
            cls._current_log_count += 1
            cls._log_count += 1

            if cls._log_filepath is None or cls._current_log_count > cls.MAX_LOG_COUNT_PER_FILE:
                cls._current_log_count = 1
                cls._log_filepath = cls._get_log_filename()

            FileUtility.appendFile(cls._log_filepath, data)
        except Exception as e:
            print(f"[Logger] Failed to write log: {e}")

    @classmethod
    async def _log_worker(cls):
        while True:
            data = await cls._queue.get()
            cls._write_log(data)

    @classmethod
    def _start_background_worker(cls):
        def start_loop():
            cls._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls._loop)
            cls._loop.create_task(cls._log_worker())
            cls._loop.run_forever()

        threading.Thread(target=start_loop, daemon=True).start()

    @classmethod
    def init(cls):
        if not cls._started:
            cls._ensure_log_dir()
            cls._start_background_worker()
            cls._started = True
            print("[Logger] Initialized")
            
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

    @classmethod
    def _format_log(cls, *args, type=LogType.INFO, sep=" ", end="\n") -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        message = sep.join(str(arg) for arg in args)
        log_entry = f"{timestamp} [{type.name}] {message}{end}"
        if cls._print_logs:
            print(log_entry, end="")
        return log_entry

    @classmethod
    def log(cls, *args, type=LogType.INFO, sep=" ", end="\n"):
        if not cls._started:
            cls.init()

        formatted = cls._format_log(*args, type=type, sep=sep, end=end)

        try:
            cls._loop.call_soon_threadsafe(cls._queue.put_nowait, formatted)
        except Exception as e:
            print(f"[Logger] Failed to enqueue log: {e}")
            cls._write_log(formatted)

    @classmethod
    def info(cls, *args, **kwargs):
        cls.log(*args, type=LogType.INFO, **kwargs)

    @classmethod
    def warning(cls, *args, **kwargs):
        cls.log(*args, type=LogType.WARNING, **kwargs)

    @classmethod
    def error(cls, *args, **kwargs):
        cls.log(*args, type=LogType.ERROR, **kwargs)

    @classmethod
    def critical(cls, *args, **kwargs):
        cls.log(*args, type=LogType.CRITICAL, **kwargs)
