import datetime
import threading
import time
from dataclasses import dataclass
from .utils.Logger import Logger
import asyncio

@dataclass
class ActionSchedulerParams:
    start_time: time
    end_time: time
    interval: int

class ActionScheduler():
    def __init__(self, params: ActionSchedulerParams):
        self.params = params
        self.action: function = None
        pass
    
    def schedule(self, action):
        if action is None:
            Logger.error("No action provided to the scheduler")
            return
        self.action = action
        self.__schedule_next()
    
    def __schedule_next(self):        
        next_run = self.__get_next_run_time()
        if not next_run:
            Logger.log("Market closed or no next run scheduled today. Please close the application and restart tomorrow before market opening")
            return

        wait_seconds = max((next_run - datetime.datetime.now()).total_seconds(), 0)
        Logger.log(f"Next run scheduled at {next_run.strftime('%H:%M:%S')} (in {wait_seconds:.1f}s)")

        def run_with_event_loop(func):
            def wrapper():
                import asyncio
                import inspect
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    if inspect.iscoroutinefunction(func):
                        loop.run_until_complete(func())
                    else:
                        func()
                finally:
                    loop.close()
            return wrapper

        def action():
            thread_target = run_with_event_loop(self.action)
            threading.Thread(target=thread_target).start()
            self.__schedule_next()

        timer = threading.Timer(wait_seconds, action)
        timer.daemon = True
        timer.start()

    def __get_next_run_time(self):
        now = datetime.datetime.now()
        today = now.date()
        
        # Start from market open today
        start = datetime.datetime.combine(today, self.params.start_time)
        end = datetime.datetime.combine(today, self.params.end_time)

        # If now is before market open
        if now < start:
            return start
        
        # If now is after market close, schedule for next day (optional behavior)
        if now > end:
            return None  # You could also return start + timedelta(days=1) to continue next day

        # Calculate next multiple of timeframe since market open
        minutes_since_open = (now - start).total_seconds() // 60
        next_multiple = ((minutes_since_open // self.params.interval) + 1) * self.params.interval
        next_run = start + datetime.timedelta(minutes=next_multiple)

        return next_run if next_run <= end else None
