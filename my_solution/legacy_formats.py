"""Legacy formats of the Neuron export, see SCHEMA.md.

- `C` text columns are padded with blanks on the right (`'BL10000001  '`).
- `N(s)` columns are integers with `s` implied decimals (`N(2)`: `123456` -> 1234.56).
- `D` columns are dates `CYYMMDD` (`1250131` -> 2025-01-31, `970630` -> 1997-06-30),
  `0` means no date (NaT) and `9999999` an open end (OPEN_END).
- `T` columns are timestamps `YYYYMMDDHHMMSS`.
"""
from decimal import Decimal

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

# Stand-in for the open end date 9999999 (pandas cannot store year 9999)
OPEN_END = pd.Timestamp('2200-12-31')
NO_DATE = 0
OPEN_END_CODE = 9999999


def to_integers(values):
    """Parse integers written as text, blanks around them and empty fields allowed.
    pyarrow parses the 6.8 million bookings about ten times faster than pd.to_numeric; text that is not an integer falls
    back to pd.to_numeric, which turns it into NaN.
    Parameters: values (pd.Series): Raw integers as text, e.g. ' 123456' or ''.
    Returns (pd.Series): int64, or float64 with NaN where a value is missing.
    """
    text = pc.utf8_trim_whitespace(pa.array(values, type=pa.string()))
    try:
        numbers = pc.cast(pc.if_else(pc.equal(text, ''), None, text), pa.int64())
    except pa.ArrowInvalid:
        return pd.to_numeric(values.str.strip().replace('', None), errors='coerce')
    return pd.Series(numbers.to_pandas().to_numpy(), index=values.index, name=values.name)


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


def decode_number(values, scale):
    """Decode fixed-point integers with `scale` implied decimals.
    Parameters: values (pd.Series): Raw integers as text, empty means no value; scale (int): Number of implied decimals.
    Returns (pd.Series): Int64 for scale 0, otherwise float64 (exact enough to explore; use `to_decimal` to calculate).
    """
    numbers = to_integers(values)
    if scale == 0:
        return numbers.astype('Int64')
    return numbers / 10 ** scale


def to_decimal(value, scale=2):
    """Convert a decoded float back into an exact Decimal with `scale` decimals.
    Parameters: value (float): Decoded value, e.g. 1234.56; scale (int): Number of decimals of the source column.
    Returns (Decimal): Exact value, e.g. Decimal('1234.56').
    """
    return Decimal(round(value * 10 ** scale)).scaleb(-scale)


def decode_text(values, scale=None):
    """Trim the blanks that pad fixed-length text on the right.
    Parameters: values (pd.Series): Raw text, e.g. 'BL10000001  '; scale: Unused, text has no decimals.
    Returns (pd.Series): Trimmed text.
    """
    return values.str.strip()


def decode_timestamp(values, scale=None):
    """Decode timestamps YYYYMMDDHHMMSS.
    Parameters: values (pd.Series): Raw timestamps, empty means no value; scale: Unused, timestamps have no decimals.
    Returns (pd.Series): Timestamps.
    """
    return pd.to_datetime(values.replace('', None), format='%Y%m%d%H%M%S')


# Decoder of every column type of NRDICT, called as decoder(raw values, scale)
DECODERS = {
    'C': decode_text,
    'N': decode_number,
    'D': lambda values, scale: decode_date(values),
    'T': decode_timestamp,
}
