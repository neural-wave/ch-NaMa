"""Building blocks of Neuron's tax module (t7): tax rates as Neuron knew them, residence, currencies, remittance dates.

- Tax rates are versioned and were sometimes corrected afterwards. Neuron used the rate it knew when it booked a tax:
  the highest version valid on the day among the versions entered before the booking; a regional rate (church tax in
  Bavaria) replaces the general one.
- The residence of a payout is the address of the policyholder valid on the payout day.
- Switzerland taxes in CHF, the other countries in EUR.
"""
import datetime as dt
from collections import defaultdict

from dateutil.relativedelta import relativedelta

TAX_CURRENCY = {'CH': 'CHF'}
# Withheld taxes are paid on this day of the next month (DE, IT) or 30 days after the end of the month (CH)
REMITTANCE_DAY = {'DE': 10, 'IT': 16}
CH_REMITTANCE_DAYS = 30


def tax_currency(country):
    """
    Currency a country taxes in.

    Parameters:
    - country (str): Country code, e.g. 'DE'.

    Returns:
    - str: 'CHF' for Switzerland, otherwise 'EUR'.
    """
    return TAX_CURRENCY.get(country, 'EUR')


def remittance_date(country, day):
    """
    Day a tax withheld on `day` was paid to the tax office.

    Parameters:
    - country (str): Country whose tax office gets the money.
    - day (datetime.date): Day of the payout.

    Returns:
    - datetime.date: Remittance date.
    """
    next_month = day.replace(day=1) + relativedelta(months=1)
    if country in REMITTANCE_DAY:
        return next_month.replace(day=REMITTANCE_DAY[country])
    return next_month - dt.timedelta(days=1) + dt.timedelta(days=CH_REMITTANCE_DAYS)


class TaxRates:
    def __init__(self, data):
        """
        Index the versioned tax rates by country and tax type.

        Parameters:
        - data (LegacyData): Decoded export.

        Returns:
        - None
        """
        table = data.table('NRTAXR')
        thresholds = [None if value != value else value for value in table.TX_THRSH]
        self.rows = defaultdict(list)
        for row, rate, threshold in zip(table.itertuples(), data.exact(table.TX_RATE), thresholds):
            self.rows[(row.TX_CNTRY, row.TX_TAXTP)].append(
                (row.TX_REGIO, row.TX_VLDFR.date(), row.TX_VLDTO.date(), row.TX_VRSNR, row.TX_CHGTS, rate, threshold))

    def rate(self, country, tax, day, known_at=None, region=''):
        """
        Rate of a tax valid on `day`, as known at `known_at`.

        Parameters:
        - country (str): Country code.
        - tax (str): Tax type, e.g. 'KST'.
        - day (datetime.date): Day the rate must be valid on.
        - known_at (pd.Timestamp): Processing time of the booking; later versions are not known yet.
        - region (str): Region of the residence, for regional rates.

        Returns:
        - tuple: (rate, threshold), (None, None) if the tax has no rate on that day.
        """
        rows = [row for row in self.rows[(country, tax)]
                if row[1] <= day <= row[2] and (known_at is None or row[4] <= known_at) and row[0] in ('', region)]
        if not rows:
            return None, None
        best = max(rows, key=lambda row: (row[0] != '', row[3]))
        return best[5], best[6]


class Residence:
    def __init__(self, data):
        """
        Index the policyholders and their addresses with their validity periods.

        Parameters:
        - data (LegacyData): Decoded export.

        Returns:
        - None
        """
        self.holders, self.addresses = defaultdict(list), defaultdict(list)
        for row in data.table('NRHOLD').sort_values('HD_VRSNR').itertuples():
            self.holders[row.HD_POLNR].append((row.HD_VLDFR.date(), row.HD_VLDTO.date(), row.HD_PERNR))
        for row in data.table('NRADDR').sort_values('AD_VRSNR').itertuples():
            self.addresses[row.AD_PERNR].append((row.AD_VLDFR.date(), row.AD_VLDTO.date(), row))
        self.persons = data.table('NRPERS').set_index('PS_PERNR').PS_BIRTH.to_dict()

    @staticmethod
    def valid(rows, day):
        """The last (highest version) of the rows valid on `day`, or None."""
        valid = [row[2] for row in rows if row[0] <= day <= row[1]]
        return valid[-1] if valid else None

    def holder(self, policy, day):
        """
        Policyholder of a policy on `day`.

        Parameters:
        - policy (str): Policy number.
        - day (datetime.date): Day.

        Returns:
        - str: Person number.
        """
        return self.valid(self.holders[policy], day) or self.holders[policy][0][2]

    def address(self, policy, day):
        """
        Address of the policyholder valid on `day`.

        Parameters:
        - policy (str): Policy number.
        - day (datetime.date): Day.

        Returns:
        - namedtuple: Row of NRADDR (country, region, reporting status, church membership).
        """
        person = self.holder(policy, day)
        return self.valid(self.addresses[person], day) or self.addresses[person][-1][2]

    def birth(self, policy, day):
        """
        Birth date of the policyholder on `day`.

        Parameters:
        - policy (str): Policy number.
        - day (datetime.date): Day.

        Returns:
        - datetime.date: Birth date.
        """
        return self.persons[self.holder(policy, day)].date()
