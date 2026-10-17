"""What the tax module of t7 works with: rates, residences, premiums, payouts, conversions and policy values.

Which taxes Neuron booked for a payout or a year is in its tax bookings (NRTAXB, without amounts); the classes built on
TaxData calculate the amounts (withholding.py, taxes.py). Amounts are rounded to the cent by system era: cut off by the
COBOL system, half up by Neuron NG.
"""
from collections import defaultdict
from decimal import Decimal

from accounting import ORDER_TYPES, ignored_events
from market import Market
from policies import policy_base
from rules import conversion_date, money
from surrender import policy_values
from tax_rules import Residence, TaxRates, tax_currency

PAYOUT_EVENTS = [400, 410, 500]
PAYOUT_BOOKINGS = ['WDR', 'SUR', 'DTH']


class TaxData:
    def __init__(self, data):
        """
        Collect what the tax calculations need: rates, residences, premiums, payouts and the tax bookings.

        Parameters:
        - data (LegacyData): Decoded export.

        Returns:
        - None
        """
        self.data, self.market, self.conversion = data, Market(data), conversion_date(data).date()
        self.rates, self.residence = TaxRates(data), Residence(data)
        self.policies = {policy.PH_POLNR: policy for policy in policy_base(data).itertuples()}
        self.bookings = data.table('NRTAXB').sort_values('TB_CHGTS', kind='stable')
        self.booked = defaultdict(set)
        for row in self.bookings.itertuples():
            self.booked[(row.TB_POLNR, row.TB_EVTNR)].add(row.TB_TAXTP)
        premiums = data.table('NRPREM').query("PR_STATE == 'P'")
        self.premiums = defaultdict(list)
        for row, amount in zip(premiums.itertuples(), data.exact(premiums.PR_AMTRC)):
            self.premiums[row.PR_POLNR].append((row.PR_RCVDT.date(), amount, row.PR_EVTNR))
        self.values = {}

    def payouts(self):
        """
        Every payout that counts: withdrawals, surrenders and death benefits that were not reversed.

        Returns:
        - dict: {policy: [(event, day, processed at, amount in policy currency, share of units sold)]}, by event.
        """
        events = self.data.table('NREVNT')
        events = events[events.EV_EVTTP.isin(PAYOUT_EVENTS)].sort_values('EV_EVTNR')
        books = self.data.select('NRBOOK', 'BK_BKTYP', ORDER_TYPES).query('BK_BKTYP in @PAYOUT_BOOKINGS')
        totals = defaultdict(Decimal)
        for policy, event, amount in zip(books.BK_POLNR, books.BK_EVTNR, self.data.exact(books.BK_AMTPC)):
            totals[(policy, event)] -= amount
        ignored = ignored_events(self.data)
        payouts = defaultdict(list)
        for row in events.itertuples():
            key = (row.EV_POLNR, row.EV_EVTNR)
            if key in ignored or key not in totals:
                continue
            share = Decimal(1) if row.EV_PCTG != row.EV_PCTG else Decimal(str(row.EV_PCTG))
            payouts[row.EV_POLNR].append((int(row.EV_EVTNR), row.EV_EFFDT.date(), row.EV_CHGTS, totals[key], share))
        return payouts

    def convert(self, amount, policy, country, day):
        """
        Convert an amount of the policy currency into the tax currency of a country, rounded by system era.

        Parameters:
        - amount (Decimal): Amount in the policy currency.
        - policy (str): Policy number.
        - country (str): Country of the tax.
        - day (datetime.date): Day of the conversion.

        Returns:
        - Decimal: Amount in the tax currency.
        """
        rate = self.market.rate(self.policies[policy].PH_CCY, day) / self.market.rate(tax_currency(country), day)
        return money(amount * rate, day < self.conversion)

    def policy_value(self, policy, day):
        """Value of a policy on `day` in its currency (the valuation of t3), cached per day."""
        if day not in self.values:
            self.values[day] = policy_values(self.data, self.market, day)
        return self.values[day].get(policy, Decimal(0))
