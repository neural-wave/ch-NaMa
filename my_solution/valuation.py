"""Historical fund holdings valued at bid, rounded by fund and pot."""
from decimal import Decimal

from ledger import ledger
from rules import conversion_date, money


def policy_values(data, market, day):
    """Value of the units of every policy on `day`, each fund and pot rounded to the cent.
    Parameters: data (LegacyData): Decoded export; market (Market): Prices and exchange rates; day (datetime.date):
        Valuation date.
    Returns (dict): {policy number: value}.
    """
    cobol = day < conversion_date(data).date()
    currency = dict(zip(data.table('NRPOLH').PH_POLNR, data.table('NRPOLH').PH_CCY))
    values = {}
    for (policy, fund, _), (days, held) in ledger(data).units.items():
        booked = days.searchsorted(day.toordinal(), side='right')
        if booked:
            units = Decimal(int(held[booked - 1])).scaleb(-6)  # millionths back to units with 6 decimals
            rate = market.fund_per_policy(fund, currency[policy], day)
            values[policy] = values.get(policy, 0) + money(units * market.bid(fund, day) / rate, cobol)
    return values
