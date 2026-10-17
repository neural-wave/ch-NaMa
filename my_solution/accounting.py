"""Fund accounting: all unit bookings of every policy, calculated from premiums, parameters and market data.

- Premium bookings (PRM) and monthly charges (ADM, AMC, RSK) are calculated (premiums.py, charges.py).
- Customer orders (switches SWO/SWI, withdrawals WDR, surrenders SUR, death benefits DTH) are complete in the
  export and taken as they are.
- Reversed events (900) and technical corrections (990) are ignored.
"""
from orders import ORDER_TYPES, REVERSAL, TECHNICAL_CORRECTION, SURRENDERED, DEATH
from orders import ignored_events, order_bookings, end_dates
import datetime as dt
import itertools
from collections import defaultdict

import pandas as pd

from charges import ChargeRun
from market import Market
from policies import policy_base
from premiums import BOOKING_COLUMNS, premium_bookings
from rules import conversion_date

REVERSAL, TECHNICAL_CORRECTION = 900, 990
SURRENDERED, DEATH = 60, 70


def policy_bookings(data, until):
    """The unit bookings of one policy after the other: premiums, customer orders and monthly charges up to `until`.
    One policy at a time, so that the 6.8 million bookings of the export never sit in memory together.
    Parameters: data (LegacyData): Decoded export; until (datetime.date): Last day of the monthly charges.
    Returns (generator): (policy number, [booking as a tuple in the columns of BOOKING_COLUMNS]).
    """
    market, conversion = Market(data), conversion_date(data).date()
    # Rows as namedtuples by policy number: much faster to read in the booking loops than pandas rows
    policies = {policy.PH_POLNR: policy for policy in policy_base(data).itertuples()}
    trades = defaultdict(list)
    orders = order_bookings(data).itertuples(index=False, name=None)
    for booking in itertools.chain(premium_bookings(data, market, policies, conversion), orders):
        trades[booking[0]].append(booking)

    run, ended = ChargeRun(data, market, conversion), end_dates(data)
    for policy, booked in trades.items():
        booked.sort(key=lambda booking: booking[5])  # by trade date
        moves = [(trade, fund, pot, units) for _, _, fund, pot, _, trade, _, _, units in booked]
        last_day = min(until, ended[policy] - dt.timedelta(days=1)) if policy in ended else until
        yield policy, booked + run.run(policies[policy], moves, last_day)


def all_bookings(data, until):
    """All unit bookings of every policy up to `until` as one table, to explore them (the tasks use ledger.py).
    Parameters: data (LegacyData): Decoded export; until (datetime.date): Last day of the monthly charges.
    Returns (pd.DataFrame): One row per booking, in the columns of BOOKING_COLUMNS.
    """
    rows = [booking for _, booked in policy_bookings(data, until) for booking in booked]
    return pd.DataFrame(rows, columns=BOOKING_COLUMNS)
