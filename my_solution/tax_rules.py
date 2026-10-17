"""Building blocks of Neuron's tax module (t7): tax rates as Neuron knew them, residence, currencies, remittance dates.

- Tax rates are versioned and were sometimes corrected afterwards. Neuron used the rate it knew when it booked a tax:
  the highest version valid on the day among the versions entered before the booking; a regional rate (church tax in
  Bavaria) replaces the general one.
- The residence of a payout is the address of the policyholder valid on the payout day, as Neuron knew it when it
  processed the payout.
- Switzerland taxes in CHF, the other countries in EUR.
"""
from tax_rates import TaxRates
from residence import Residence
import datetime as dt

from dateutil.relativedelta import relativedelta

TAX_CURRENCY = {'CH': 'CHF'}
# Withheld taxes are paid on this day of the next month (DE, IT) or 30 days after the end of the month (CH)
REMITTANCE_DAY = {'DE': 10, 'IT': 16}
CH_REMITTANCE_DAYS = 30


def tax_currency(country):
    """Currency a country taxes in.
    Parameters: country (str): Country code, e.g. 'DE'.
    Returns (str): 'CHF' for Switzerland, otherwise 'EUR'.
    """
    return TAX_CURRENCY.get(country, 'EUR')


def remittance_date(country, day):
    """Nominal remittance deadline, moved to Monday if it falls on a weekend.

    Weekend adjustment is the T7 MONDAY experiment, pending organizer feedback.
    Parameters: country (str): Country whose tax office gets the money; day (datetime.date): Day of the payout.
    Returns (datetime.date): Remittance date.
    """
    next_month = day.replace(day=1) + relativedelta(months=1)
    if country in REMITTANCE_DAY:
        remitted = next_month.replace(day=REMITTANCE_DAY[country])
    else:
        remitted = next_month - dt.timedelta(days=1) + dt.timedelta(days=CH_REMITTANCE_DAYS)
    weekday = remitted.weekday()
    return remitted + dt.timedelta(days=7 - weekday) if weekday >= 5 else remitted
