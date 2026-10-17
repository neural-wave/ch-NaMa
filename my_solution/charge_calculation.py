"""Admin, management and risk charges at one monthly anniversary.

Positions are valued at bid with the day's FX and rounded to cents. Admin fees
are capped at the total value and allocated proportionally. Management charges
use the pot's tariff or agreement, with actual days/360 in COBOL and 1/12 later.
Risk is calculated on the value left after admin and management charges.

Allocation sends the rounding remainder to the largest position. Nonzero charges
cancel units, rounded to six decimals; zero amounts produce no booking.
"""
from decimal import Decimal

from charge_allocation import split
from charge_parameters import ChargeParameters
from risk import SMOKER, sum_at_risk
from rules import money, units


class ChargeCalculation(ChargeParameters):
    def charge(self, policy, day, previous, positions, age):
        """
        The admin fee, management charge and risk charge of one monthly anniversary.

        Parameters:
        - policy (namedtuple): Row of `policy_base`.
        - day (datetime.date): Monthly anniversary.
        - previous (datetime.date): The anniversary before (for the days of the COBOL management charge).
        - positions (dict): {(fund, pot): units} held before the day.
        - age (int): Age of the insured person in this policy year.

        Returns:
        - list: Bookings (policy, type, fund, pot, money date, trade date, gross, amount, units).
        """
        cobol = day < self.conversion
        tariff = self.tariff(policy, day)
        rates = {position: self.market.fund_per_policy(position[0], policy.PH_CCY, day) for position in positions}
        bids = {position: self.market.bid(position[0], day) for position in positions}
        values = {position: money(held * bids[position] / rates[position], cobol) for position, held in positions.items()}

        admin = split(min(tariff.CG_ADMFEE, sum(values.values())), values, cobol)
        period = Decimal((day - previous).days) / 360 if cobol else Decimal(1) / 12
        management = {position: money(value * self.management_rate(policy, position[1], tariff, day) * period, cobol)
                      for position, value in values.items()}
        left = {position: values[position] - admin[position] - management[position] for position in values}

        qx = self.mortality[(tariff.CG_MORTTB, policy.SEX, age)]
        smoker = tariff.CG_SMKFAC if policy.PS_SMOKE == SMOKER else 1
        risk = sum_at_risk(policy.OPTION, sum(left.values()), policy.RK_SUMIN) * qx * (1 + policy.RK_LOAD) * smoker / 12
        risk = split(money(risk, cobol), left, cobol)

        bookings = []
        for kind, amounts in [('ADM', admin), ('AMC', management), ('RSK', risk)]:
            for (fund, pot), amount in amounts.items():
                if amount:
                    cancelled = units(amount * rates[(fund, pot)] / bids[(fund, pot)], cobol)
                    bookings.append((policy.PH_POLNR, kind, fund, pot, None, day, None, amount, -cancelled))
        return bookings
