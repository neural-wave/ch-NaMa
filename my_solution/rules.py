"""Building blocks that every task uses: loading, parameter lookups, money rounding and the system change."""
import calendar
import datetime as dt
import functools
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from legacy_loader import LegacyData

CENT = Decimal('0.01')
UNIT = Decimal('0.000001')
SYSTEM_CONVERSION = 800


@functools.cache
def load(legacy_dir):
    """
    Load the export once, all tasks share the decoded tables.

    Parameters:
    - legacy_dir (str): Folder with the NR*.csv files.

    Returns:
    - LegacyData: Decoded export.
    """
    return LegacyData(legacy_dir)


def conversion_date(data):
    """
    Day of the conversion from the COBOL system to Neuron NG (event 800, 2007-08-11 in this export).

    Parameters:
    - data (LegacyData): Decoded export.

    Returns:
    - pd.Timestamp: Conversion day.
    """
    events = data.table('NREVNT')
    return events[events.EV_EVTTP == SYSTEM_CONVERSION].EV_EFFDT.min()


def extract_date(data):
    """
    Day of the export: the effective date of its last event (2026-06-30).

    Parameters:
    - data (LegacyData): Decoded export.

    Returns:
    - datetime.date: Extract date.
    """
    return data.table('NREVNT').EV_EFFDT.max().date()


def valid_on_date(items, date_column, table, prefix, on, keep_all=False):
    """
    Attach to each item the row of `table` that is valid on the item's own date.

    A row is valid if VLDFR <= date <= VLDTO; if several are valid, the highest version VRSNR wins.

    Parameters:
    - items (pd.DataFrame): Rows that need a parameter, e.g. premium items.
    - date_column (str): Column of `items` with the date that decides, e.g. 'PR_RCVDT'.
    - table (pd.DataFrame): Table with a validity period, e.g. NRPOLH or NRCOMR.
    - prefix (str): Two-letter alias of `table`, e.g. 'PH'.
    - on (dict): {column of items: column of table} to join on, empty for a table without keys (e.g. NRILLU).
    - keep_all (bool): Keep the items without a valid row (with empty table columns), e.g. for agreements.

    Returns:
    - pd.DataFrame: The items joined with their valid row.
    """
    # Find the valid row with the keys and dates only: merging all columns first takes gigabytes for the premiums
    items = items.reset_index(drop=True)
    periods = [column for column in [f'{prefix}_VLDFR', f'{prefix}_VLDTO', f'{prefix}_VRSNR'] if column in table]
    rows = table[list(dict.fromkeys(list(on.values()) + periods))].reset_index(drop=True).reset_index(names='row')
    dates = items[list(on) + [date_column]].reset_index(names='item')
    merged = dates.merge(rows, left_on=list(on), right_on=list(on.values())) if on else dates.merge(rows, how='cross')
    valid = merged[(merged[f'{prefix}_VLDFR'] <= merged[date_column]) & (merged[date_column] <= merged[f'{prefix}_VLDTO'])]
    if f'{prefix}_VRSNR' in valid:
        valid = valid.sort_values(f'{prefix}_VRSNR')
    valid = valid.drop_duplicates('item', keep='last').sort_values('item')

    found = table.iloc[valid.row.to_numpy()].set_axis(valid.item.to_numpy())
    found = found.drop(columns=[column for column in found if column in items])
    if keep_all:
        return items.join(found)
    return items.loc[valid.item.to_numpy()].join(found).reset_index(drop=True)


def money(amount, truncate=False):
    """
    Round an exact amount to the cent: half up in Neuron NG, cut off (truncated) in the COBOL system.

    Parameters:
    - amount (Decimal): Exact amount, e.g. Decimal('399.205').
    - truncate (bool): True for a value the COBOL system calculated.

    Returns:
    - Decimal: Rounded amount, e.g. Decimal('399.21') (truncated: Decimal('399.20')).
    """
    return amount.quantize(CENT, ROUND_DOWN if truncate else ROUND_HALF_UP)


def units(number, truncate=False):
    """
    Round a number of fund units to 6 decimals: half up in Neuron NG, truncated in the COBOL system.

    Parameters:
    - number (Decimal): Exact number of units.
    - truncate (bool): True for units the COBOL system calculated.

    Returns:
    - Decimal: Rounded units.
    """
    return number.quantize(UNIT, ROUND_DOWN if truncate else ROUND_HALF_UP)


def add_months(day, months):
    """
    Add whole months to a date, cutting the day to the end of a shorter month (as dateutil's relativedelta does).

    About ten times faster than relativedelta, which matters in the monthly loops over 30 years of policies.

    Parameters:
    - day (datetime.date): Start, e.g. 2007-01-31.
    - months (int): Number of months to add.

    Returns:
    - datetime.date: e.g. 2007-02-28 for one month.
    """
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    return dt.date(year, month + 1, min(day.day, calendar.monthrange(year, month + 1)[1]))
