"""Stamp duties of the tax module (t7).

- Italy (BOL): every 31 December the policy value is taxed at the rate known when Neuron booked it; a payout books
  the share of its year; a later correction of a rate re-books every earlier year at the rate known at the
  correction. The accrued duty is collected (BOC) when money is paid out.
- Switzerland (STP): a duty on the premiums Neuron booked it for, in CHF.
"""
from premium_tax import premium_stamp_duty
import datetime as dt
from decimal import Decimal

from rules import money


def stamp_duty(module, policy, payouts):
    """
    Italian stamp duty (BOL) bookings of a policy, in the order Neuron booked them.

    Year-end bookings tax the policy value of 31 December at the rate known then; a payout books the share of its
    year; a later correction re-books every earlier year at the rate known at the correction.

    Parameters:
    - module (TaxModule): Rates, bookings, conversions and policy values.
    - policy (str): Policy number.
    - payouts (list): Payouts of the policy, as from TaxModule.payouts.

    Returns:
    - list: [(day, amount)]
    """
    paid = {event: (day, amount) for event, day, _, amount, _ in payouts}
    booked_years, result = {}, []
    for row in module.bookings[(module.bookings.TB_POLNR == policy) & (module.bookings.TB_TAXTP == 'BOL')].itertuples():
        day = row.TB_EFFDT.date()
        if row.TB_EVTNR in paid:
            rate, _ = module.rates.rate('IT', 'BOL', day, row.TB_CHGTS)
            value = module.convert(paid[row.TB_EVTNR][1], policy, 'IT', day)
            elapsed = Decimal((day - dt.date(day.year, 1, 1)).days) / 365
            result.append((day, money(value * rate * elapsed, day < module.conversion)))
        elif (day.month, day.day) == (12, 31):
            value = module.convert(module.policy_value(policy, day), policy, 'IT', day)
            rate, _ = module.rates.rate('IT', 'BOL', day, row.TB_CHGTS)
            booked_years[day] = (value, money(value * rate, day < module.conversion))
            result.append((day, booked_years[day][1]))
        else:
            correction = Decimal(0)
            for year_end, (value, old) in booked_years.items():
                rate, _ = module.rates.rate('IT', 'BOL', year_end, row.TB_CHGTS)
                new = money(value * rate, day < module.conversion)
                booked_years[year_end], correction = (value, new), correction + new - old
            result.append((day, correction))
    return result
