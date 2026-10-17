"""Premium bookings (PRM): every paid premium buys units of the funds of its allocation, less the entry charge.

Everything is decided on the money date: the allocation, the broker tier, the entry charge and the pot (premiums of
the first `PD_INIMON` months buy initial units, pot 1). Each fund buys on its own: on the first day after the money
date that the fund has a price, at the issue (ask) price, converted with the exchange rate of the day before.
"""
import datetime as dt

import pandas as pd
from dateutil.relativedelta import relativedelta

from rules import money, units, valid_on_date

PAID = 'P'
# Columns of a booking: gross is the premium share before the entry charge (premium bookings only)
BOOKING_COLUMNS = ['policy', 'type', 'fund', 'pot', 'money_date', 'trade', 'gross', 'amount', 'units']


def allocated_premiums(data):
    """
    One row per paid premium and fund, with the allocation share and the entry charge rate of the money date.

    Parameters:
    - data (LegacyData): Decoded export.

    Returns:
    - pd.DataFrame: Premium items joined with their allocation, broker tier and entry charge rate.
    """
    premiums = data.table('NRPREM').query('PR_STATE == @PAID')

    # The allocation version valid on the money date, with all its funds
    allocated = premiums.merge(data.table('NRALLO'), left_on='PR_POLNR', right_on='AL_POLNR')
    allocated = allocated[(allocated.AL_VLDFR <= allocated.PR_RCVDT) & (allocated.PR_RCVDT <= allocated.AL_VLDTO)]
    newest = allocated.groupby(['PR_POLNR', 'PR_DUENR']).AL_VRSNR.transform('max')
    allocated = allocated[allocated.AL_VRSNR == newest]

    # Entry charge of the broker tier, replaced by an individual agreement while one is valid
    allocated = valid_on_date(allocated, 'PR_RCVDT', data.table('NRPOLH'), 'PH', {'PR_POLNR': 'PH_POLNR'})
    allocated = allocated.merge(data.table('NRBROK'), left_on='PH_BRKNR', right_on='BR_BRKNR')
    allocated = valid_on_date(allocated, 'PR_RCVDT', data.table('NRENTC'), 'EC', {'BR_TIER': 'EC_TIER'})
    agreements = data.table('NRAGRE').query("AG_FEETP == 'ENT'")
    allocated = valid_on_date(allocated, 'PR_RCVDT', agreements, 'AG', {'PR_POLNR': 'AG_POLNR'}, keep_all=True)
    allocated['ENTRY_RATE'] = allocated.AG_RATE.fillna(allocated.EC_RATE)
    return allocated


def premium_bookings(data, market, policies, conversion):
    """
    Premium bookings of all paid premiums.

    Parameters:
    - data (LegacyData): Decoded export.
    - market (Market): Prices and exchange rates.
    - policies (dict): {policy number: row of `policy_base`}
    - conversion (datetime.date): Day of the system conversion.

    Returns:
    - pd.DataFrame: One row per booking: policy, type, fund, pot, money date, trade date, gross, amount, units.
    """
    allocated = allocated_premiums(data)
    received, shares = data.exact(allocated.PR_AMTRC), data.exact(allocated.AL_PCTG)
    entry_rates = data.exact(allocated.ENTRY_RATE, scale=6)

    rows = []
    for item, gross, share, entry in zip(allocated.itertuples(), received, shares, entry_rates):
        policy = policies[item.PR_POLNR]
        money_date = item.PR_RCVDT.date()
        initial_end = (policy.PH_BEGDT + relativedelta(months=int(policy.PD_INIMON))).date()
        trade, ask = market.purchase(item.AL_FNDID, money_date)
        cobol = trade < conversion
        amount = money(gross * share * (1 - entry), cobol)
        rate = market.fund_per_policy(item.AL_FNDID, policy.PH_CCY, trade - dt.timedelta(days=1))
        rows.append((item.PR_POLNR, 'PRM', item.AL_FNDID, '1' if money_date < initial_end else '2', money_date,
                     trade, gross * share, amount, units(amount * rate / ask, cobol)))
    return pd.DataFrame(rows, columns=BOOKING_COLUMNS)

