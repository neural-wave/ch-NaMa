"""Advance holdings through the monthly charge anniversaries of a policy.

The charge run sees trades strictly before the anniversary. ChargeCalculation
computes that day's admin, management and risk bookings; their unit cancellations
are applied before proceeding to the next month. Public ChargeRun and split
imports remain available here for the accounting and research tools.
"""
from charge_allocation import split
from charge_calculation import ChargeCalculation
import itertools
from collections import defaultdict
from decimal import Decimal

from risk import entry_age
from rules import add_months


class ChargeRun(ChargeCalculation):
    def run(self, policy, trades, until):
        """
        All monthly charges of a policy from the first monthly anniversary up to `until`.

        Parameters:
        - policy (namedtuple): Row of `policy_base`.
        - trades (list): Premium and order bookings (trade date, fund, pot, units), sorted by trade date.
        - until (datetime.date): Last day to charge.

        Returns:
        - list: Charge bookings.
        """
        holdings, bookings, waiting = defaultdict(Decimal), [], iter(trades + [(None, None, None, None)])
        trade = next(waiting)
        begin, previous = policy.PH_BEGDT.date(), policy.PH_BEGDT.date()
        age = entry_age(policy.PS_BIRTH, policy.PH_BEGDT, policy.PH_APPDT.date() < self.conversion)
        for month in itertools.count(1):
            day = add_months(begin, month)
            if day > until:
                return bookings
            while trade[0] is not None and trade[0] < day:
                holdings[(trade[1], trade[2])] += trade[3]
                trade = next(waiting)
            positions = {position: held for position, held in holdings.items() if held > 0}
            if positions:
                charged = self.charge(policy, day, previous, positions, age + month // 12)
                for booking in charged:
                    holdings[(booking[2], booking[3])] += booking[8]
                bookings += charged
            previous = day
