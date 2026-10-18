"""Premium basis and German adjustments used to report a payout gain."""
import datetime as dt
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from rules import money
from tax_data import TaxData


HALF_INCOME = {'held': 12, 'age': 60, 'later age': 62, 'from': dt.date(2005, 1, 1), 'later from': dt.date(2012, 1, 1)}


class PayoutBasis(TaxData):
    def premium_basis(self, policy, day, withdrawals, country):
        """Unrounded remaining premium basis in tax currency before this payout.

        Each premium is converted on receipt, then reduced by subsequent shares
        withdrawn. Round only the share allocated to the current payout. Kept as
        a separate step so the research trace can inspect the actual calculation.
        """
        basis = Decimal(0)
        for paid_day, premium, _ in self.premiums[policy]:
            if paid_day <= day:
                left = self.convert(premium, policy, country, paid_day)
                for withdrawn_day, withdrawn in withdrawals:
                    if withdrawn_day >= paid_day:
                        left *= 1 - withdrawn
                basis += left
        return basis

    def gain(self, policy, payout, withdrawals, country):
        """
        Gain in tax currency: customer benefit less premiums belonging to the share paid out.

        Parameters:
        - policy (str): Policy number.
        - payout (tuple): (event, day, processed at, amount, share).
        - withdrawals (list): Earlier payouts of the policy as (day, share).
        - country (str): Country of the tax.

        Returns:
        - Decimal: Gain (negative for a loss).
        """
        _, day, _, _, share = payout
        basis = self.premium_basis(policy, day, withdrawals, country)
        return self.convert(self.amount_paid(policy, payout), policy, country, day) - money(
            basis * share, day < self.conversion)

    def german_base(self, policy, day, gain):
        """
        Taxable part of a gain in Germany: only half after 12 years from 60 (Neuron applied no partial exemption).

        Parameters:
        - policy (str): Policy number.
        - day (datetime.date): Day of the payout.
        - gain (Decimal): Gain in EUR.

        Returns:
        - Decimal: Taxable base.
        """
        base = gain
        terms = self.policies[policy]
        applied = terms.PH_APPDT.date()
        age = HALF_INCOME['later age'] if applied >= HALF_INCOME['later from'] else HALF_INCOME['age']
        if (applied >= HALF_INCOME['from'] and relativedelta(day, terms.PH_BEGDT.date()).years >= HALF_INCOME['held']
                and relativedelta(day, self.residence.birth(policy, day)).years >= age):
            share, _ = self.rates.rate('DE', 'HEV', day)
            base *= share or 1
        return money(base, day < self.conversion)
