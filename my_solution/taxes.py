"""t7: what Neuron's tax module withheld, accrued and reported, per payout and per year.

The inputs are in tax_data.py, the taxes withheld from a payout in withholding.py and the Italian and Swiss stamp
duties in stamp_duty.py; this module puts them together for every policy.
"""
import functools
from collections import defaultdict
from decimal import Decimal

from rules import money
from stamp_duty import premium_stamp_duty, stamp_duty
from tax_rules import remittance_date
from withholding import Withholding

ANNUAL_TAXES = ['STP', 'VST', 'SOS', 'BOL', 'KST', 'SOL', 'KIS']


class TaxModule(Withholding):
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
