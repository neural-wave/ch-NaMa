"""t7: the taxes withheld from a payout (withdrawal, surrender, death benefit).

- Gain of a payout: the customer benefit (after penalty or including insured death benefit), in tax currency,
  less the premiums paid, each one
  converted on the day it was received (and reduced by the shares already withdrawn), times the share now withdrawn.
- CH: withholding tax (VST) on the whole payout in CHF.
- IT: substitute tax (SOS) on the gain, each rate on the part accrued while it was valid (policy value at the changes).
- DE: capital gains tax (KST) on the gain, only half of it (HEV) after 12 years and from the age of 60 (62 from 2012),
  reduced by church tax (base x rate / (1 + rate x church rate)); solidarity surcharge (SOL) and church tax (KIS) on the
  KST; German cents are cut off.
"""
from payout_basis import HALF_INCOME, PayoutBasis
from decimal import Decimal

from rules import money

WITHHOLDING = {'CH': 'VST', 'IT': 'SOS', 'DE': 'KST'}


class Withholding(PayoutBasis):
    def withholding(self, policy, payout, withdrawals, country, region):
        """
        Report the amount subject to a booked withholding tax; otherwise report zero.

        This candidate uses zero for the taxable base of untaxed payouts. The
        research comparison also tests reporting their economic gain or loss.

        Returns:
        - tuple: (base, withheld, surcharges, {tax type: amount})
        """
        event, day, known, _, _ = payout
        booked, cobol = self.booked[(policy, event)], day < self.conversion
        tax = WITHHOLDING.get(country)
        if tax not in booked:
            return self.untaxed_base(policy, payout, country), Decimal('0.00'), Decimal('0.00'), {}
        if country == 'CH':
            base = self.convert(self.amount_paid(policy, payout), policy, country, day)
        elif country in ('IT', 'DE'):
            base = self.gain(policy, payout, withdrawals, country)
            base = self.german_base(policy, day, base) if country == 'DE' else base
        else:
            base = Decimal('0.00')
        rate, _ = self.rates.rate(country, tax, day, known)
        church, _ = self.rates.rate(country, 'KIS', day, known, region) if 'KIS' in booked else (None, None)
        if country == 'IT':
            withheld = money(self.italian_tax(policy, payout, withdrawals, base), cobol)
        elif country == 'DE':  # church tax reduces the capital gains tax; German cents are cut off (public samples)
            withheld = money(base * rate / (1 + rate * (church or 0)), True)
        else:
            withheld = money(base * rate, cobol)
        amounts = {tax: withheld}
        for surcharge in ['SOL', 'KIS']:
            surcharge_rate, _ = self.rates.rate(country, surcharge, day, known, region)
            if surcharge in booked and surcharge_rate is not None:
                amounts[surcharge] = money(withheld * surcharge_rate, cobol or country == 'DE')
        return base, withheld, sum(amounts.get(name, Decimal('0.00')) for name in ['SOL', 'KIS']), amounts

    def untaxed_base(self, policy, payout, country):
        """Base of a payout nothing was withheld from (public samples): in Switzerland the amount paid in CHF, elsewhere
        0.00."""
        _, day, _, _, _ = payout
        if country != 'CH':
            return Decimal('0.00')
        return self.convert(self.amount_paid(policy, payout), policy, country, day)

    def italian_tax(self, policy, payout, withdrawals, gain):
        """
        Italian substitute tax: each rate on the part of the gain accrued while it was valid (public samples).

        The gain up to a rate change is the policy value converted on its last day less the premium basis then, for the
        units this payout sells; the rest of the gain takes the rate of the payout day. Rounded once by the caller.
        """
        _, day, known, _, share = payout
        begin, tax, before = self.policies[policy].PH_BEGDT.date(), Decimal(0), Decimal(0)
        for change in self.rates.changes('IT', 'SOS', known):
            if begin <= change < day:
                remaining = share
                for withdrawn_day, withdrawn in withdrawals:
                    remaining *= 1 - withdrawn if withdrawn_day > change else 1
                earlier = [(withdrawn_day, withdrawn) for withdrawn_day, withdrawn in withdrawals if withdrawn_day <= change]
                accrued = remaining * (self.convert(self.policy_value(policy, change), policy, 'IT', change)
                                       - self.premium_basis(policy, change, earlier, 'IT'))
                rate, _ = self.rates.rate('IT', 'SOS', change, known)
                tax, before = tax + rate * (accrued - before), accrued
        rate, _ = self.rates.rate('IT', 'SOS', day, known)
        return tax + rate * (gain - before)

    def reported_tax(self, policy, payout, address):
        """Swiss tax on a payout above the threshold of a holder who did not object: reported, not withheld."""
        _, day, known, _, _ = payout
        rate, limit = self.rates.rate('CH', 'VST', day, known)
        amount = self.convert(self.amount_paid(policy, payout), policy, 'CH', day)
        if address.AD_TAXST == 'E' or rate is None or amount <= limit:
            return Decimal('0.00')
        return money(amount * rate, day < self.conversion)
