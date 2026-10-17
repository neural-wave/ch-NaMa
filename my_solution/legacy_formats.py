"""Legacy formats of the Neuron export, see SCHEMA.md.

- `C` text columns are padded with blanks on the right (`'BL10000001  '`).
- `N(s)` columns are integers with `s` implied decimals (`N(2)`: `123456` -> 1234.56).
- `D` columns are dates `CYYMMDD` (`1250131` -> 2025-01-31, `970630` -> 1997-06-30),
  `0` means no date (NaT) and `9999999` an open end (OPEN_END).
- `T` columns are timestamps `YYYYMMDDHHMMSS`.
"""
from decimal import Decimal

import pandas as pd

# Stand-in for the open end date 9999999 (pandas cannot store year 9999)
OPEN_END = pd.Timestamp('2200-12-31')
NO_DATE = 0
OPEN_END_CODE = 9999999


def decode_date(values):
    """
    Decode legacy dates CYYMMDD into timestamps.

    Parameters:
    - values (pd.Series): Raw dates as text, e.g. '1250131' or '970630'.

    Returns:
    - pd.Series: Timestamps, NaT for 0 or empty, OPEN_END for 9999999.
    """
    codes = pd.to_numeric(values, errors='coerce').fillna(NO_DATE).astype('int64')
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
    """
    Find legacy dates CYYMMDD whose day does not exist in its month (e.g. 541131 = 31 Nov 1954).

    Parameters:
    - values (pd.Series): Raw dates as text.

    Returns:
    - pd.Series: The raw values that `decode_date` had to clamp.
    """
    codes = pd.to_numeric(values, errors='coerce').fillna(NO_DATE).astype('int64')
    real = codes[(codes != NO_DATE) & (codes != OPEN_END_CODE)]
    yyyymmdd = (19000000 + real).astype(str)
    return values[real.index][pd.to_datetime(yyyymmdd, format='%Y%m%d', errors='coerce').isna()]


def decode_number(values, scale):
    """
    Decode fixed-point integers with `scale` implied decimals.

    Parameters:
    - values (pd.Series): Raw integers as text, empty means no value.
    - scale (int): Number of implied decimals.

    Returns:
    - pd.Series: Int64 for scale 0, otherwise float64 (exact enough to explore; use `to_decimal` to calculate).
    """
    numbers = pd.to_numeric(values.str.strip().replace('', None), errors='coerce')
    if scale == 0:
        return numbers.astype('Int64')
    return numbers / 10 ** scale


def to_decimal(value, scale=2):
    """
    Convert a decoded float back into an exact Decimal with `scale` decimals.

    Parameters:
    - value (float): Decoded value, e.g. 1234.56.
    - scale (int): Number of decimals of the source column.

    Returns:
    - Decimal: Exact value, e.g. Decimal('1234.56').
    """
    return Decimal(round(value * 10 ** scale)).scaleb(-scale)


def decode_text(values, scale=None):
    """
    Trim the blanks that pad fixed-length text on the right.

    Parameters:
    - values (pd.Series): Raw text, e.g. 'BL10000001  '.
    - scale: Unused, text has no decimals.

    Returns:
    - pd.Series: Trimmed text.
    """
    return values.str.strip()


def decode_timestamp(values, scale=None):
    """
    Decode timestamps YYYYMMDDHHMMSS.

    Parameters:
    - values (pd.Series): Raw timestamps, empty means no value.
    - scale: Unused, timestamps have no decimals.

    Returns:
    - pd.Series: Timestamps.
    """
    return pd.to_datetime(values.replace('', None), format='%Y%m%d%H%M%S')


# Decoder of every column type of NRDICT, called as decoder(raw values, scale)
DECODERS = {
    'C': decode_text,
    'N': decode_number,
    'D': lambda values, scale: decode_date(values),
    'T': decode_timestamp,
}
