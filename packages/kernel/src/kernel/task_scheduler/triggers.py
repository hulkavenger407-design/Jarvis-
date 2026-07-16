import datetime

from croniter import croniter

from .interfaces import Trigger


class OneShotTrigger(Trigger):
    def next_execution(self, last_run: datetime.datetime | None = None) -> datetime.datetime | None:
        return None if last_run else datetime.datetime.now(datetime.UTC)


class IntervalTrigger(Trigger):
    def __init__(self, interval_seconds: float):
        self.interval = datetime.timedelta(seconds=interval_seconds)

    def next_execution(self, last_run: datetime.datetime | None = None) -> datetime.datetime | None:
        now = datetime.datetime.now(datetime.UTC)
        if not last_run:
            return now
        return now + self.interval


class CronTrigger(Trigger):
    def __init__(self, cron_expr: str):
        self.cron_expr = cron_expr

    def next_execution(self, last_run: datetime.datetime | None = None) -> datetime.datetime | None:
        now = datetime.datetime.now(datetime.UTC)
        base = last_run or now
        iter = croniter(self.cron_expr, base)
        return iter.get_next(datetime.datetime)
