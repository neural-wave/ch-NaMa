"""Infer recurring closures from weekdays with and without fund prices."""
import datetime as dt
from collections import defaultdict


MIN_YEARS = 3


def weekdays(first, last):
    """All Mondays to Fridays from `first` to `last`.
    Parameters: first (datetime.date): First day; last (datetime.date): Last day.
    Returns (list): Weekdays as datetime.date.
    """
    days = (first + dt.timedelta(days=offset) for offset in range((last - first).days + 1))
    return [day for day in days if day.weekday() < 5]


def closed_keys(days, open_days, key):
    """The keys (e.g. the date in the year) of the weekdays that never have a price.
    Parameters: days (list): Weekdays of the observed period; open_days (set): Days with prices; key (callable):
        key(day), e.g. (month, day) or the days after Easter Sunday.
    Returns (set): Keys seen closed in at least MIN_YEARS years and never open.
    """
    seen = defaultdict(lambda: [0, 0])  # key -> [closed, open]
    for day in days:
        seen[key(day)][day in open_days] += 1
    return {value for value, (closed, opened) in seen.items() if opened == 0 and closed >= MIN_YEARS}
