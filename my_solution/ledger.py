"""What t3, t4 and t7 need from the 6.8 million bookings of the fund accounting, collected policy by policy.

Keeping every booking in memory took 8 GB; the ledger keeps the units held per position and day (exact integers in
millionths of a unit) and the charges per policy and year.
"""
import functools
from collections import defaultdict, namedtuple
from decimal import Decimal

import numpy as np

from accounting import policy_bookings
from rules import extract_date

CHARGE_COLUMNS = {'ADM': 1, 'AMC': 2, 'RSK': 3}
MILLION = 1_000_000  # units have 6 decimals: held in millionths they are exact integers

Ledger = namedtuple('Ledger', ['units', 'charges'])


@functools.cache
def ledger(data):
    """
    What the tasks need from all bookings up to the extract date, collected policy by policy.

    Parameters:
    - data (LegacyData): Decoded export.

    Returns:
    - Ledger:
      units: {(policy, fund, pot): (trade days as ordinals, units held after each day in millionths)}, numpy
      arrays, so that a valuation on any day (t3, t7) is one search per position;
      charges: {(policy, year of the trade date): [entry, admin, management, risk]} for the statements (t4).
    """
    units, charges = {}, defaultdict(lambda: [Decimal(0)] * 4)
    for policy, booked in policy_bookings(data, extract_date(data)):
        moves = defaultdict(list)
        for _, kind, fund, pot, _, trade, gross, amount, held in booked:
            moves[(fund, pot)].append((trade.toordinal(), int(held * MILLION)))
            if kind == 'PRM':
                charges[(policy, trade.year)][0] += gross - amount
            elif kind in CHARGE_COLUMNS:
                charges[(policy, trade.year)][CHARGE_COLUMNS[kind]] += amount
        for (fund, pot), changes in moves.items():
            changes.sort(key=lambda change: change[0])
            units[(policy, fund, pot)] = (np.array([day for day, _ in changes]),
                                          np.cumsum([change for _, change in changes]))
    return Ledger(units, charges)
