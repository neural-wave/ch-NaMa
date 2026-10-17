"""Building blocks that every task uses: loading, parameter lookups, money rounding and the system change."""
from validity import valid_on_date
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
    """Cache one LegacyData per export folder so all tasks share decoded tables."""
    return LegacyData(legacy_dir)


def conversion_date(data):
    """Return the first system-conversion event's effective date as a Timestamp.

    Event 800 marks the COBOL-to-Neuron NG conversion (2007-08-11 here)."""
    events = data.table('NREVNT')
    return events[events.EV_EVTTP == SYSTEM_CONVERSION].EV_EFFDT.min()


def extract_date(data):
    """Return the last event's effective date, 2026-06-30 in this export."""
    return data.table('NREVNT').EV_EFFDT.max().date()


def money(amount, truncate=False):
    """Quantize a Decimal to cents using the legacy system's rounding mode.

    truncate=True cuts off towards zero (COBOL); otherwise round half up."""
    return amount.quantize(CENT, ROUND_DOWN if truncate else ROUND_HALF_UP)


def units(number, truncate=False):
    """Quantize Decimal fund units to six places, truncating or rounding half up."""
    return number.quantize(UNIT, ROUND_DOWN if truncate else ROUND_HALF_UP)


def add_months(day, months):
    """Add whole months to a date, clamping to the destination month's last day.

    Equivalent to relativedelta for these dates, but faster in the monthly loops."""
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    return dt.date(year, month + 1, min(day.day, calendar.monthrange(year, month + 1)[1]))
