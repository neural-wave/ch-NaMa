"""t7: the taxes withheld from a payout (withdrawal, surrender, death benefit).

- Gain of a payout: the payout converted into the tax currency on the payout day, less the premiums paid, each one
  converted on the day it was received (and reduced by the shares already withdrawn), times the share now withdrawn.
- CH: withholding tax (VST) on the whole payout in CHF.
- IT: substitute tax (SOS) on the gain.
- DE: capital gains tax (KST) on the gain, less the partial exemption (TFS) from 2018 and only half of it (HEV) after
  12 years and from the age of 60 (62 from 2012); solidarity surcharge (SOL) and church tax (KIS) on the KST.
"""
import datetime as dt
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from rules import money
from tax_data import TaxData

WITHHOLDING = {'CH': 'VST', 'IT': 'SOS', 'DE': 'KST'}
HALF_INCOME = {'held': 12, 'age': 60, 'later age': 62, 'from': dt.date(2005, 1, 1), 'later from': dt.date(2012, 1, 1)}


class Withholding(TaxData):
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

    def withholding(self, policy, payout, withdrawals, country, region):
        """
        Taxable base, withheld tax and surcharges of a payout, for the taxes Neuron booked.

        Returns:
        - tuple: (base, withheld, surcharges, {tax type: amount})
        """
        event, day, known, amount, _ = payout
        booked, cobol = self.booked[(policy, event)], day < self.conversion
        tax = WITHHOLDING.get(country)
        if tax not in booked:
            return Decimal('0.00'), Decimal('0.00'), Decimal('0.00'), {}
        if country == 'CH':
            base = self.convert(amount, policy, country, day)
        else:
            base = max(self.gain(policy, payout, withdrawals, country), Decimal(0))
            base = self.german_base(policy, day, base) if country == 'DE' else base
        rate, _ = self.rates.rate(country, tax, day, known)
        withheld = money(base * rate, cobol)
        amounts = {tax: withheld}
        for surcharge in ['SOL', 'KIS']:
            surcharge_rate, _ = self.rates.rate(country, surcharge, day, known, region)
            if surcharge in booked and surcharge_rate is not None:
                amounts[surcharge] = money(withheld * surcharge_rate, cobol)
        return base, withheld, sum(amounts.get(name, Decimal(0)) for name in ['SOL', 'KIS']), amounts
