"""Tax rows and annual movements for the payouts of one policy.

The holder's residence on the effective day selects the reporting country.
Withholding uses the booked tax types, while the reported base is calculated
separately. Italian duty accruals and duty already collected are tracked across
payouts; earlier withdrawals also reduce the premium basis of later gains.

Each payout returns country, base, withholding, surcharges, stamp duty and
remittance date (None if nothing was withheld). Annual movements retain their individual tax-type amounts.
"""
import datetime as dt
from collections import defaultdict
from decimal import Decimal

from business_calendar import calendar
from rules import money
from stamp_duty import stamp_duty
from tax_rules import month_end_plus_30, remittance_date
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
            reported = self.reported_tax(policy, payout, address) if country == 'CH' and not withheld else 0
            if reported:  # the Swiss tax reported instead of withheld counts as Swiss tax in the annual table
                yearly[(day.year, 'REPORTED')] += reported
            remitted = None  # Switzerland 30 days after the end of the month, Italy on the 16th, Germany on the 10th
            if withheld + surcharges > 0:  # counted from the month the money was paid (PD_PAYDAY business days later)
                paid = day
                for _ in range(int(self.policies[policy].PD_PAYDAY)):
                    paid = calendar(self.data).next_business_day(paid + dt.timedelta(days=1))
                remitted = month_end_plus_30(paid) if country == 'CH' else remittance_date(country, paid)
            if remitted:  # a deadline on a closed day moves to the next business day; in Switzerland 2 January is closed
                remitted = calendar(self.data).next_business_day(remitted)
                while country == 'CH' and (remitted.month, remitted.day) == (1, 2):
                    remitted = calendar(self.data).next_business_day(remitted + dt.timedelta(days=1))
            for tax, amount in amounts.items():  # a withheld tax counts in the year it was remitted
                yearly[((remitted or day).year, tax)] += amount
            rows[event] = (country, base, withheld, surcharges, stamp, remitted)
            withdrawals.append((day, share))
        return rows, yearly
