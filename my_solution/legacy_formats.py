"""Legacy formats of the Neuron export, see SCHEMA.md.

- `C` text columns are padded with blanks on the right (`'BL10000001  '`).
- `N(s)` columns are integers with `s` implied decimals (`N(2)`: `123456` -> 1234.56).
- `D` columns are dates `CYYMMDD` (`1250131` -> 2025-01-31, `970630` -> 1997-06-30),
  `0` means no date (NaT) and `9999999` an open end (OPEN_END).
- `T` columns are timestamps `YYYYMMDDHHMMSS`.
"""
from legacy_dates import OPEN_END, NO_DATE, OPEN_END_CODE, decode_date, invalid_dates, decode_timestamp
from legacy_numbers import to_integers, decode_number, to_decimal



def decode_text(values, scale=None):
    """Trim the blanks that pad fixed-length text on the right.
    Parameters: values (pd.Series): Raw text, e.g. 'BL10000001  '; scale: Unused, text has no decimals.
    Returns (pd.Series): Trimmed text.
    """
    return values.str.strip()


# Decoder of every column type of NRDICT, called as decoder(raw values, scale)
DECODERS = {
    'C': decode_text,
    'N': decode_number,
    'D': lambda values, scale: decode_date(values),
    'T': decode_timestamp,
}
