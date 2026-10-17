"""Reusable age and day-count candidates for convention search.

Age candidates accept a birth date and valuation day and return whole years.
The nearest-birthday candidate adds six calendar months; day-based candidates
divide elapsed days by 365 or 365.25 before rounding.

Day-count candidates accept the start and end of a period and return a Decimal
fraction of a year. The monthly convention always returns 1/12; actual-day
conventions use elapsed days, and 30/360 caps each day of month at 30.
"""
from decimal import Decimal

from dateutil.relativedelta import relativedelta


def age_last_birthday(birth, day):
    """Completed years of age on `day`."""
    return relativedelta(day, birth).years


def age_nearest_birthday(birth, day):
    """Age at the birthday nearest to `day` (completed years six months later)."""
    return relativedelta(day + relativedelta(months=6), birth).years


def age_days_365(birth, day):
    """Days since birth / 365, rounded (leap days ignored, as some old systems did)."""
    return int((day - birth).days / 365 + 0.5)


def age_days_36525(birth, day):
    """Days since birth / 365.25, rounded."""
    return int((day - birth).days / 365.25 + 0.5)


def twelfth(start, end):
    """Monthly share of a yearly rate: 1 / 12 (exact Decimal, like all day counts)."""
    return Decimal(1) / 12


def actual_360(start, end):
    """Actual days / 360."""
    return Decimal((end - start).days) / 360


def actual_365(start, end):
    """Actual days / 365."""
    return Decimal((end - start).days) / 365


def thirty_360(start, end):
    """30 / 360: every month counts 30 days."""
    days = (end.year - start.year) * 360 + (end.month - start.month) * 30 + min(end.day, 30) - min(start.day, 30)
    return Decimal(days) / 360
