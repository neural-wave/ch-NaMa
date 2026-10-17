"""Business calendar learned from fund-price publication days.

Recurring weekday closures are fixed dates or offsets from Easter, inferred by
calendar_learning. The resulting rules also apply to future years."""
from calendar_learning import MIN_YEARS, weekdays, closed_keys
import datetime as dt
import functools

from dateutil.easter import easter

# A rule must be seen on a weekday in at least this many years, so that a one-off closure is not taken for a holiday


class BusinessCalendar:
    def __init__(self, open_days):
        """Learn holiday rules from an iterable of price days as datetime.date."""
        open_days = set(open_days)
        days = weekdays(min(open_days), max(open_days))
        self.fixed = sorted(closed_keys(days, open_days, lambda day: (day.month, day.day)))
        self.after_easter = sorted(closed_keys(days, open_days, lambda day: (day - easter(day.year)).days))
        self.cache = {}

    def holidays(self, year):
        """Return the cached set of holidays for a calendar year.

        Fixed 29 February closures are excluded when constructing this set."""
        if year not in self.cache:
            fixed = {dt.date(year, month, day) for month, day in self.fixed if (month, day) != (2, 29)}
            self.cache[year] = fixed | {easter(year) + dt.timedelta(days=offset) for offset in self.after_easter}
        return self.cache[year]

    def is_business_day(self, day):
        """True for a Monday-Friday date outside the learned holidays."""
        return day.weekday() < 5 and day not in self.holidays(day.year)

    def next_business_day(self, day):
        """Return the first business day on or after the supplied date."""
        while not self.is_business_day(day):
            day += dt.timedelta(days=1)
        return day


@functools.cache
def calendar(data):
    """Return the cached calendar of a LegacyData export.

    A date is open if at least one fund published a price on it."""
    return BusinessCalendar(day.date() for day in data.table('NRFPRC').FP_PRCDT.unique())
