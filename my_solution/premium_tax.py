"""Swiss stamp duty on booked premium events, in CHF by receipt year."""
from collections import defaultdict
from decimal import Decimal

from rules import money


def premium_stamp_duty(module):
    """
    Swiss stamp duty (STP) on the premiums Neuron booked it for, by policy and year.

    Parameters:
    - module (TaxModule): Rates, bookings, premiums and conversions.

    Returns:
    - dict: {(policy, year): amount in CHF}
    """
    yearly = defaultdict(Decimal)
    for row in module.bookings[module.bookings.TB_TAXTP == 'STP'].itertuples():
        premium = [(day, amount) for day, amount, event in module.premiums[row.TB_POLNR] if event == row.TB_EVTNR]
        if premium:
            day = premium[0][0]
            rate, _ = module.rates.rate('CH', 'STP', day, row.TB_CHGTS)
            yearly[(row.TB_POLNR, day.year)] += money(module.convert(premium[0][1], row.TB_POLNR, 'CH', day) * rate,
                                                      day < module.conversion)
    return yearly
