from datetime import datetime, time, timezone


def utc_now():
    return datetime.now(timezone.utc)


def utc_day_bounds(from_date, to_date):
    start = datetime.combine(from_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(to_date, time.max, tzinfo=timezone.utc)
    return start, end
