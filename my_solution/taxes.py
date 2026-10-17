"""t7: what Neuron's tax module withheld, accrued and reported.

Which taxes Neuron booked for a payout or a year is in its tax bookings (NRTAXB, without amounts); this module
calculates the amounts:

- Gain of a payout: the payout converted into the tax currency on the payout day, less the premiums paid, each one
  converted on the day it was received (and reduced by the shares already withdrawn), times the share now withdrawn.
- CH: withholding tax (VST) on the whole payout in CHF.
- IT: substitute tax (SOS) on the gain; the stamp duties are in stamp_duty.py.
- DE: capital gains tax (KST) on the gain, less the partial exemption (TFS) from 2018 and only half of it (HEV) after
  12 years and from the age of 60 (62 from 2012); solidarity surcharge (SOL) and church tax (KIS) on the KST.
- Amounts are rounded to the cent by system era: cut off by the COBOL system, half up by Neuron NG.
"""
import datetime as dt
import functools
from collections import defaultdict
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from accounting import ignored_events
from market import Market
from policies import policy_base
from rules import conversion_date, money
from stamp_duty import premium_stamp_duty, stamp_duty
from surrender import policy_values
from tax_rules import Residence, TaxRates, remittance_date, tax_currency

PAYOUT_EVENTS = [400, 410, 500]
PAYOUT_BOOKINGS = ['WDR', 'SUR', 'DTH']
WITHHOLDING = {'CH': 'VST', 'IT': 'SOS', 'DE': 'KST'}
ANNUAL_TAXES = ['STP', 'VST', 'SOS', 'BOL', 'KST', 'SOL', 'KIS']
HALF_INCOME = {'held': 12, 'age': 60, 'later age': 62, 'from': dt.date(2005, 1, 1), 'later from': dt.date(2012, 1, 1)}


class TaxModule:
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
        books = self.data.table('NRBOOK').query('BK_BKTYP in @PAYOUT_BOOKINGS')
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

    def policy_value(self, policy, day):
        """Value of a policy on `day` in its currency (the valuation of t3), cached per day."""
        if day not in self.values:
            self.values[day] = policy_values(self.data, self.market, day)
        return self.values[day].get(policy, Decimal(0))

    def policy_taxes(self, policy, payouts):
        """
        Payout rows and yearly amounts of one policy.

        Returns:
        - tuple: ({event: payout row}, {(year, tax type): amount})
        """
        rows, yearly, withdrawals = {}, defaultdict(Decimal), []
        accruals = stamp_duty(self, policy, payouts)
        for day, amount in accruals:
            yearly[(day.year, 'BOL')] += amount
        collected = Decimal(0)
        for payout in payouts:
            event, day, _, _, share = payout
            address = self.residence.address(policy, day)
            country = address.AD_CNTRY
            base, withheld, surcharges, amounts = self.withholding(policy, payout, withdrawals, country, address.AD_REGIO)
            stamp = Decimal('0.00')
            if 'BOC' in self.booked[(policy, event)]:
                accrued = sum(amount for accrued_day, amount in accruals if accrued_day <= day) - collected
                stamp = money(accrued * share, day < self.conversion)
                collected += stamp
            for tax, amount in amounts.items():
                yearly[(day.year, tax)] += amount
            remitted = remittance_date(country, day) if withheld + surcharges > 0 else (
                remittance_date('IT', day) if stamp > 0 else None)
            rows[event] = (country, base, withheld, surcharges, stamp, remitted)
            withdrawals.append((day, share))
        return rows, yearly


@functools.cache
def tax_results(data):
    """
    Payout rows and annual amounts of every policy.

    Parameters:
    - data (LegacyData): Decoded export.

    Returns:
    - tuple: ({(policy, event): payout row}, {(policy, year): annual row})
    """
    module = TaxModule(data)
    payout_rows, yearly = {}, defaultdict(lambda: [Decimal('0.00')] * len(ANNUAL_TAXES))
    all_payouts = module.payouts()
    for policy, payouts in all_payouts.items():
        rows, amounts = module.policy_taxes(policy, payouts)
        payout_rows.update({(policy, event): row for event, row in rows.items()})
        for (year, tax), amount in amounts.items():
            yearly[(policy, year)][ANNUAL_TAXES.index(tax)] += amount
    for policy in {row.TB_POLNR for row in module.bookings.itertuples() if row.TB_TAXTP == 'BOL'} - set(all_payouts):
        for day, amount in stamp_duty(module, policy, []):
            yearly[(policy, day.year)][ANNUAL_TAXES.index('BOL')] += amount
    for (policy, year), amount in premium_stamp_duty(module).items():
        yearly[(policy, year)][ANNUAL_TAXES.index('STP')] += amount
    annual = {key: tuple(values) for key, values in yearly.items() if any(values)}
    return payout_rows, annual
