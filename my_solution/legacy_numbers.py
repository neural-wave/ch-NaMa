"""Numeric legacy fields: raw integer parsing, implied decimals and exact money."""
from decimal import Decimal

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc


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
