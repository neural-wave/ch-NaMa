"""Tax rows and annual movements for the payouts of one policy.

The holder's residence on the effective day selects the reporting country.
Withholding uses the booked tax types, while the reported base is calculated
separately. Italian duty accruals and duty already collected are tracked across
payouts; earlier withdrawals also reduce the premium basis of later gains.

Each payout returns country, base, withholding, surcharges, stamp duty and
remittance date (None if nothing was withheld). Annual movements retain their
individual tax-type amounts.
"""
from collections import defaultdict
from decimal import Decimal

from rules import money
from stamp_duty import stamp_duty
from tax_rules import remittance_date
from withholding import Withholding


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
            event, day, known, _, share = payout
            address = self.residence.address(policy, day, known)
            country = address.AD_CNTRY
            base, withheld, surcharges, amounts = self.withholding(policy, payout, withdrawals, country, address.AD_REGIO)
            stamp = Decimal('0.00')
            if 'BOC' in self.booked[(policy, event)]:
                accrued = sum(amount for accrued_day, amount in accruals if accrued_day <= day) - collected
                stamp = money(accrued * share, day < self.conversion)
                collected += stamp
            for tax, amount in amounts.items():
                yearly[(day.year, tax)] += amount
            remitted = remittance_date(country, day) if withheld + surcharges > 0 else None
            rows[event] = (country, base, withheld, surcharges, stamp, remitted)
            withdrawals.append((day, share))
        return rows, yearly
