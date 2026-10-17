"""Business calendar of NeuralWave Life: Monday to Friday without the public holidays of Ticino."""
import datetime as dt
import functools

from dateutil.easter import easter

# Ticino holidays, checked against every day without fund prices from 1993 to 2026 (no difference)
FIXED_HOLIDAYS = [(1, 1), (1, 6), (3, 19), (5, 1), (6, 29), (8, 1), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)]
# Days after Easter Sunday: Easter Monday, Ascension, Whit Monday, Corpus Christi (Good Friday is a business day)
EASTER_HOLIDAYS = [1, 39, 50, 60]


@functools.cache
def holidays(year):
    """
    All public holidays of one year in Ticino.

    Parameters:
    - year (int): Calendar year.

    Returns:
    - set: Holidays as datetime.date.
    """
    easter_sunday = easter(year)
    fixed = {dt.date(year, month, day) for month, day in FIXED_HOLIDAYS}
    return fixed | {easter_sunday + dt.timedelta(days=offset) for offset in EASTER_HOLIDAYS}


def is_business_day(day):
    """
    Check if a day is a working day: Monday to Friday and no holiday.

    Parameters:
    - day (datetime.date): Day to check.

    Returns:
    - bool: True for a business day.
    """
    return day.weekday() < 5 and day not in holidays(day.year)


def next_business_day(day):
    """
    The day itself if it is a business day, otherwise the next business day.

    Parameters:
    - day (datetime.date): Starting day.

    Returns:
    - datetime.date: First business day on or after `day`.
    """
    while not is_business_day(day):
        day += dt.timedelta(days=1)
    return day
