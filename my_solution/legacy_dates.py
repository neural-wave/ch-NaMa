"""Legacy dates and timestamps, including open ends and invalid month days."""
import pandas as pd

from legacy_numbers import to_integers


# Stand-in for the open end date 9999999 (pandas cannot store year 9999)
OPEN_END = pd.Timestamp('2200-12-31')
NO_DATE = 0
OPEN_END_CODE = 9999999


def decode_date(values):
    """Decode legacy dates CYYMMDD into timestamps.
    Parameters: values (pd.Series): Raw dates as text, e.g. '1250131' or '970630'.
    Returns (pd.Series): Timestamps, NaT for 0 or empty, OPEN_END for 9999999.
    """
    codes = to_integers(values).fillna(NO_DATE).astype('int64')
    real = (codes != NO_DATE) & (codes != OPEN_END_CODE)

    # CYYMMDD: the century digit C counts from 1900
    year = 1900 + codes[real] // 10000
    month = codes[real] // 100 % 100
    month_start = pd.to_datetime(pd.DataFrame({'year': year, 'month': month, 'day': 1}))

    # COBOL accepted impossible days such as 31 November: clamp them to the last day of the month
    day = (codes[real] % 100).clip(upper=month_start.dt.days_in_month)

    dates = pd.Series(pd.NaT, index=values.index, dtype='datetime64[ns]')
    dates[real] = month_start + pd.to_timedelta(day - 1, unit='D')
    dates[codes == OPEN_END_CODE] = OPEN_END
    return dates


def invalid_dates(values):
    """Find legacy dates CYYMMDD whose day does not exist in its month (e.g. 541131 = 31 Nov 1954).
    Parameters: values (pd.Series): Raw dates as text.
    Returns (pd.Series): The raw values that `decode_date` had to clamp.
    """
    codes = to_integers(values).fillna(NO_DATE).astype('int64')
    real = codes[(codes != NO_DATE) & (codes != OPEN_END_CODE)]
    month, day = real // 100 % 100, real % 100
    month_start = pd.to_datetime(pd.DataFrame({'year': 1900 + real // 10000, 'month': month.clip(1, 12), 'day': 1}))
    impossible = (month < 1) | (month > 12) | (day < 1) | (day > month_start.dt.days_in_month)
    return values[real.index][impossible]


def decode_timestamp(values, scale=None):
    """Decode timestamps YYYYMMDDHHMMSS.
    Parameters: values (pd.Series): Raw timestamps, empty means no value; scale: Unused, timestamps have no decimals.
    Returns (pd.Series): Timestamps.
    """
    return pd.to_datetime(values.replace('', None), format='%Y%m%d%H%M%S')
