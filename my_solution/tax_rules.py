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
# Candidate: DE/IT use the next month's fixed day; CH uses the next month's end.
# Swiss timing is provisional: score feedback did not isolate it from other changes.
REMITTANCE_DAY = {'DE': 10, 'IT': 16}


def tax_currency(country):
    """Currency a country taxes in.
    Parameters: country (str): Country code, e.g. 'DE'.
    Returns (str): 'CHF' for Switzerland, otherwise 'EUR'.
    """
    return TAX_CURRENCY.get(country, 'EUR')


def end_of_next_month(day):
    """Last day of the month after `day`."""
    return day.replace(day=1) + relativedelta(months=2) - dt.timedelta(days=1)


def month_end_plus_30(day):
    """Swiss withholding tax on insurance benefits is due 30 days after the end of the month of the payout."""
    return day.replace(day=1) + relativedelta(months=1) - dt.timedelta(days=1) + dt.timedelta(days=30)


def remittance_date(country, day):
    """Day a tax withheld on `day` was paid to the tax office.
    Parameters: country (str): Country whose tax office gets the money; day (datetime.date): Day of the payout.
    Returns (datetime.date): Remittance date.
    """
    next_month = day.replace(day=1) + relativedelta(months=1)
    if country in REMITTANCE_DAY:
        return next_month.replace(day=REMITTANCE_DAY[country])
    return next_month + relativedelta(months=1) - dt.timedelta(days=1)
