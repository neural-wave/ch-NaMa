"""t4: annual statement of every policy and calendar year.

From the start year to the year the policy ends by surrender or death, at the latest 2025:

- premiums: the paid premiums received in the year (money date);
- entry charges: premium share less the amount invested, of the premium bookings traded in the year;
- admin fees, management fees, risk charges: the monthly charges booked in the year (fund accounting of t3);
- total charges: entry charges + admin fees + management fees + risk charges.
"""
from collections import defaultdict
from decimal import Decimal

from accounting import end_dates
from ledger import ledger
from premiums import PAID
from rules import money

LAST_YEAR = 2025


def yearly_charges(data):
    """Entry, admin, management and risk charges of every policy and year of the trade date.
    Parameters: data (LegacyData): Decoded export.
    Returns (dict): {(policy number, year): [entry, admin, management, risk]}.
    """
    return ledger(data).charges


def yearly_premiums(data):
    """Paid premiums of every policy and year of the money date.
    Parameters: data (LegacyData): Decoded export.
    Returns (dict): {(policy number, year): premiums}.
    """
    paid = data.table('NRPREM').query('PR_STATE == @PAID')
    sums = defaultdict(Decimal)
    for policy, day, amount in zip(paid.PR_POLNR, paid.PR_RCVDT, data.exact(paid.PR_AMTRC)):
        sums[(policy, day.year)] += amount
    return sums


def annual_statements(data):
    """Annual statement of every policy and calendar year.
    Parameters: data (LegacyData): Decoded export.
    Returns (dict): {(policy number, year): (premiums, entry, admin, management, risk, total)}.
    """
    premiums, charges, ended = yearly_premiums(data), yearly_charges(data), end_dates(data)
    starts = data.table('NRPOLH').groupby('PH_POLNR').PH_BEGDT.min()
    result = {}
    for policy, start in starts.items():
        last = min(ended[policy].year, LAST_YEAR) if policy in ended else LAST_YEAR
        for year in range(start.year, last + 1):
            entry, admin, management, risk = charges[(policy, year)]
            entry = money(entry)
            total = entry + admin + management + risk
            result[(policy, year)] = (premiums[(policy, year)], entry, admin, management, risk, total)
    return result
