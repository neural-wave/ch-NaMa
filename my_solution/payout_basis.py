"""Premium basis and German adjustments used to report a payout gain."""
import datetime as dt
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from rules import money
from tax_data import TaxData


HALF_INCOME = {'held': 12, 'age': 60, 'later age': 62, 'from': dt.date(2005, 1, 1), 'later from': dt.date(2012, 1, 1)}


class PayoutBasis(TaxData):
    def gain(self, policy, payout, withdrawals, country):
        """
        Gain of a payout in the tax currency: payout less the premiums that belong to the share paid out.

        Parameters:
        - policy (str): Policy number.
        - payout (tuple): (event, day, processed at, amount, share).
        - withdrawals (list): Earlier payouts of the policy as (day, share).
        - country (str): Country of the tax.

        Returns:
        - Decimal: Gain (negative for a loss).
        """
        _, day, _, amount, share = payout
        basis = Decimal(0)
        for paid_day, premium, _ in self.premiums[policy]:
            if paid_day <= day:
                left = self.convert(premium, policy, country, paid_day)
                for withdrawn_day, withdrawn in withdrawals:
                    if withdrawn_day >= paid_day:
                        left *= 1 - withdrawn
                basis += left
        return self.convert(amount, policy, country, day) - money(basis * share, day < self.conversion)

    def german_base(self, policy, day, gain):
        """
        Taxable part of a gain in Germany: less the partial exemption, and only half after 12 years from 60.

        Parameters:
        - policy (str): Policy number.
        - day (datetime.date): Day of the payout.
        - gain (Decimal): Gain in EUR.

        Returns:
        - Decimal: Taxable base.
        """
        exemption, _ = self.rates.rate('DE', 'TFS', day)
        base = gain * (1 - (exemption or 0))
        terms = self.policies[policy]
        applied = terms.PH_APPDT.date()
        age = HALF_INCOME['later age'] if applied >= HALF_INCOME['later from'] else HALF_INCOME['age']
        if (applied >= HALF_INCOME['from'] and relativedelta(day, terms.PH_BEGDT.date()).years >= HALF_INCOME['held']
                and relativedelta(day, self.residence.birth(policy, day)).years >= age):
            share, _ = self.rates.rate('DE', 'HEV', day)
            base *= share or 1
        return money(base, day < self.conversion)
