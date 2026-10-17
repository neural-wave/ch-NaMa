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
# Neuron's tax job ran on the 10th of every month (the year-end stamp duty is processed on 10 January): withheld
# taxes of a month are paid on the 10th of the next month, for every country
REMITTANCE_DAY = 10


def tax_currency(country):
    """Currency a country taxes in.
    Parameters: country (str): Country code, e.g. 'DE'.
    Returns (str): 'CHF' for Switzerland, otherwise 'EUR'.
    """
    return TAX_CURRENCY.get(country, 'EUR')


def remittance_date(country, day):
    """Day a tax withheld on `day` was paid to the tax office.
    Parameters: country (str): Country whose tax office gets the money; day (datetime.date): Day of the payout.
    Returns (datetime.date): Remittance date.
    """
    return (day.replace(day=1) + relativedelta(months=1)).replace(day=REMITTANCE_DAY)
