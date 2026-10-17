"""Fund accounting: all unit bookings of every policy, calculated from premiums, parameters and market data.

- Premium bookings (PRM) and monthly charges (ADM, AMC, RSK) are calculated (premiums.py, charges.py).
- Customer orders (switches SWO/SWI, withdrawals WDR, surrenders SUR, death benefits DTH) are complete in the
  export and taken as they are.
- Reversed events (900) and technical corrections (990) are ignored.
"""
import datetime as dt
import functools

import pandas as pd

from charges import ChargeRun
from market import Market
from policies import policy_base
from premiums import BOOKING_COLUMNS, premium_bookings
from rules import conversion_date, extract_date

ORDER_TYPES = ['SWO', 'SWI', 'WDR', 'SUR', 'DTH']
REVERSAL, TECHNICAL_CORRECTION = 900, 990
SURRENDERED, DEATH = 60, 70


def ignored_events(data):
    """
    Events whose bookings do not count: reversed events and technical corrections.

    Parameters:
    - data (LegacyData): Decoded export.

    Returns:
    - set: {(policy number, event number)}
    """
    events = data.table('NREVNT')
    reversals = events[events.EV_EVTTP == REVERSAL]
    corrections = events[events.EV_EVTTP == TECHNICAL_CORRECTION]
    return set(zip(reversals.EV_POLNR, reversals.EV_REVNR)) | set(zip(corrections.EV_POLNR, corrections.EV_EVTNR))


def order_bookings(data):
    """
    Bookings of the customer orders, as they are in the export.

    Parameters:
    - data (LegacyData): Decoded export.

    Returns:
    - pd.DataFrame: One row per booking, in the columns of BOOKING_COLUMNS.
    """
    orders = data.table('NRBOOK').query('BK_BKTYP in @ORDER_TYPES')
    ignored = ignored_events(data)
    orders = orders[[(policy, event) not in ignored for policy, event in zip(orders.BK_POLNR, orders.BK_EVTNR)]]
    return pd.DataFrame({
        'policy': orders.BK_POLNR.values, 'type': orders.BK_BKTYP.values, 'fund': orders.BK_FNDID.values,
        'pot': orders.BK_POTCD.values, 'money_date': None, 'trade': [day.date() for day in orders.BK_TRDDT],
        'gross': None, 'amount': data.exact(orders.BK_AMTPC), 'units': data.exact(orders.BK_UNITS)})


def end_dates(data):
    """
    Day a policy ended by surrender or death: from this day on there are no more monthly charges.

    Parameters:
    - data (LegacyData): Decoded export.

    Returns:
    - dict: {policy number: datetime.date}
    """
    ended = data.table('NRPOLH').query('PH_STATE in [@SURRENDERED, @DEATH]').groupby('PH_POLNR').PH_VLDFR.min()
    return {policy: day.date() for policy, day in ended.items()}


def all_bookings(data, until):
    """
    All unit bookings of every policy up to `until`.

    Parameters:
    - data (LegacyData): Decoded export.
    - until (datetime.date): Last day of the monthly charges.

    Returns:
    - pd.DataFrame: One row per booking, in the columns of BOOKING_COLUMNS.
    """
    market, conversion = Market(data), conversion_date(data).date()
    # Rows as namedtuples by policy number: much faster to read in the booking loops than pandas rows
    policies = {policy.PH_POLNR: policy for policy in policy_base(data).itertuples()}
    trades = pd.concat([premium_bookings(data, market, policies, conversion), order_bookings(data)])
    trades = trades.sort_values('trade', kind='stable')

    run, ended = ChargeRun(data, market, conversion), end_dates(data)
    charges = []
    for policy, rows in trades.groupby('policy', sort=False):
        moves = list(zip(rows.trade, rows.fund, rows.pot, rows.units))
        last_day = min(until, ended[policy] - dt.timedelta(days=1)) if policy in ended else until
        charges += run.run(policies[policy], moves, last_day)
    return pd.concat([trades, pd.DataFrame(charges, columns=BOOKING_COLUMNS)], ignore_index=True)


@functools.cache
def bookings(data):
    """
    All bookings up to the extract date (the last event of the export), shared by t3 and t4.

    Parameters:
    - data (LegacyData): Decoded export.

    Returns:
    - pd.DataFrame: Result of `all_bookings`.
    """
    return all_bookings(data, extract_date(data))
