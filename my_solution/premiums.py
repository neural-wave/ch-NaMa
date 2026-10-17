"""Premium bookings (PRM): every paid premium buys units of the funds of its allocation, less the entry charge.

Everything is decided on the money date: the allocation, the broker tier, the entry charge and the pot (premiums of
the first `PD_INIMON` months buy initial units, pot 1). Each fund buys on its own: on the first day after the money
date that the fund has a price, at the issue (ask) price, converted with the exchange rate of the day before.
"""
from premium_allocation import PAID, allocated_premiums
import datetime as dt

from rules import add_months, money, units, valid_on_date

# Columns of a booking: gross is the premium share before the entry charge (premium bookings only)
BOOKING_COLUMNS = ['policy', 'type', 'fund', 'pot', 'money_date', 'trade', 'gross', 'amount', 'units']


def premium_bookings(data, market, policies, conversion):
    """Premium bookings of all paid premiums.
    Parameters: data (LegacyData): Decoded export; market (Market): Prices and exchange rates; policies (dict): {policy
        number: row of `policy_base`}; conversion (datetime.date): Day of the system conversion.
    Returns (list): Bookings as tuples in the columns of BOOKING_COLUMNS (plain tuples need far less memory than a
        table).
    """
    allocated = allocated_premiums(data)
    received, shares = data.exact(allocated.PR_AMTRC), data.exact(allocated.AL_PCTG)
    entry_rates = data.exact(allocated.ENTRY_RATE, scale=6)

    rows = []
    items = allocated[['PR_POLNR', 'PR_RCVDT', 'AL_FNDID']].itertuples()
    for item, gross, share, entry in zip(items, received, shares, entry_rates):
        policy = policies[item.PR_POLNR]
        money_date = item.PR_RCVDT.date()
        initial_end = add_months(policy.PH_BEGDT.date(), int(policy.PD_INIMON))
        trade, ask = market.purchase(item.AL_FNDID, money_date)
        cobol = trade < conversion
        amount = money(gross * share * (1 - entry), cobol)
        rate = market.fund_per_policy(item.AL_FNDID, policy.PH_CCY, trade - dt.timedelta(days=1))
        rows.append((item.PR_POLNR, 'PRM', item.AL_FNDID, '1' if money_date < initial_end else '2', money_date,
                     trade, gross * share, amount, units(amount * rate / ask, cobol)))
    return rows
