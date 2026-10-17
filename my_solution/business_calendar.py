"""Business calendar learned from the market data: Monday to Friday, without the holidays.

Fund prices are published on every business day, so every weekday without any price is a holiday. The calendar learns
the holidays as rules that also work for future years: fixed dates (month, day) and days after Easter Sunday that never
have a price when they fall on a weekday. For this export the learned rules are exactly the public holidays of Ticino.
"""
import datetime as dt
import functools
from collections import defaultdict

from dateutil.easter import easter

# A rule must be seen on a weekday in at least this many years, so that a one-off closure is not taken for a holiday
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


class BusinessCalendar:
    def __init__(self, open_days):
        """Learn the holiday rules from the days that have prices.
        Parameters: open_days (iterable): Days with at least one price, as datetime.date.
        """
        open_days = set(open_days)
        days = weekdays(min(open_days), max(open_days))
        self.fixed = sorted(closed_keys(days, open_days, lambda day: (day.month, day.day)))
        self.after_easter = sorted(closed_keys(days, open_days, lambda day: (day - easter(day.year)).days))
        self.cache = {}

    def holidays(self, year):
        """All holidays of one year.
        Parameters: year (int): Calendar year.
        Returns (set): Holidays as datetime.date.
        """
        if year not in self.cache:
            fixed = {dt.date(year, month, day) for month, day in self.fixed if (month, day) != (2, 29)}
            self.cache[year] = fixed | {easter(year) + dt.timedelta(days=offset) for offset in self.after_easter}
        return self.cache[year]

    def is_business_day(self, day):
        """Check if a day is a working day: Monday to Friday and no holiday.
        Parameters: day (datetime.date): Day to check.
        Returns (bool): True for a business day.
        """
        return day.weekday() < 5 and day not in self.holidays(day.year)

    def next_business_day(self, day):
        """The day itself if it is a business day, otherwise the next business day.
        Parameters: day (datetime.date): Starting day.
        Returns (datetime.date): First business day on or after `day`.
        """
        while not self.is_business_day(day):
            day += dt.timedelta(days=1)
        return day


@functools.cache
def calendar(data):
    """The business calendar of an export, learned from its fund price days.
    Parameters: data (LegacyData): Decoded export.
    Returns (BusinessCalendar): Learned calendar.
    """
    return BusinessCalendar(day.date() for day in data.table('NRFPRC').FP_PRCDT.unique())
