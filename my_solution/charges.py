"""Monthly charges: on every monthly anniversary Neuron cancels units in all funds and pots.

The charge run of a day sees the units traded before that day. Every position (fund and pot) is valued at the bid
price on or before the day, converted into the policy currency with the rate of the day and rounded to the cent.

- ADM: the admin fee valid on the day, split over the positions in proportion to their value.
- AMC: value x rate of the pot (or of an agreement) / 12; the COBOL system charged rate x days / 360.
- RSK: sum at risk x qx x (1 + loading) x smoker factor / 12, the sum at risk on the value left after admin fee and
  management charge, split in proportion to the value each position has left.

A split gives the rounding difference to the largest position; positions with a share of 0.00 get no booking.
"""
import itertools
from collections import defaultdict
from decimal import Decimal


from risk import SMOKER, entry_age, mortality_table, sum_at_risk
from rules import add_months, money, units

TARIFF_COLUMNS = ['CG_VLDFR', 'CG_VLDTO', 'CG_ADMFEE', 'CG_AMCP1', 'CG_AMCP2', 'CG_SMKFAC', 'CG_MORTTB']


def split(total, weights, cobol):
    """
    Split an amount over the positions in proportion to their weights.

    Parameters:
    - total (Decimal): Amount to split.
    - weights (dict): {position: weight}
    - cobol (bool): True for a booking of the COBOL system (truncated amounts).

    Returns:
    - dict: {position: share}, the largest position takes the rounding difference (but never goes below 0).
    """
    weight_sum = sum(weights.values())
    if not total or weight_sum <= 0:
        return {position: Decimal(0) for position in weights}
    shares = {position: money(total * weight / weight_sum, cobol) for position, weight in weights.items()}
    largest = max(weights, key=weights.get)
    shares[largest] = max(shares[largest] + total - sum(shares.values()), Decimal(0))
    return shares


class ChargeRun:
    def __init__(self, data, market, conversion):
        """
        Parameters of the monthly charges: tariff charges by tariff family and generation, AMC agreements, mortality.

        Parameters:
        - data (LegacyData): Decoded export.
        - market (Market): Prices and exchange rates.
        - conversion (datetime.date): Day of the system conversion.

        Returns:
        - None
        """
        self.market, self.conversion = market, conversion
        self.mortality = mortality_table(data)
        tariffs = data.table('NRCHRG')
        for column in ['CG_ADMFEE', 'CG_AMCP1', 'CG_AMCP2', 'CG_SMKFAC']:
            tariffs[column] = data.exact(tariffs[column])
        self.tariffs = defaultdict(list)
        for row in tariffs.itertuples():
            self.tariffs[(row.CG_TARFAM, row.CG_TARGEN)].append((row.CG_VLDFR.date(), row.CG_VLDTO.date(), row))
        agreements = data.table('NRAGRE').query("AG_FEETP == 'AMC'")
        self.agreements = defaultdict(list)
        for row, rate in zip(agreements.itertuples(), data.exact(agreements.AG_RATE)):
            self.agreements[row.AG_POLNR].append((row.AG_VLDFR.date(), row.AG_VLDTO.date(), rate))

    def tariff(self, policy, day):
        """
        Charges of the tariff of the policy valid on `day`.

        Parameters:
        - policy (namedtuple): Row of `policy_base`.
        - day (datetime.date): Charge day.

        Returns:
        - namedtuple: Row of NRCHRG.
        """
        return next(row for start, end, row in self.tariffs[(policy.TARFAM, policy.TARGEN)] if start <= day <= end)

    def management_rate(self, policy, pot, tariff, day):
        """
        Yearly management charge of a pot: an agreement valid on `day` replaces the rate of the tariff.

        Parameters:
        - policy (namedtuple): Row of `policy_base`.
        - pot (str): '1' initial units, '2' base units.
        - tariff (namedtuple): Row of NRCHRG valid on `day`.
        - day (datetime.date): Charge day.

        Returns:
        - Decimal: Yearly rate.
        """
        agreed = [rate for start, end, rate in self.agreements[policy.PH_POLNR] if start <= day <= end]
        return agreed[-1] if agreed else (tariff.CG_AMCP1 if pot == '1' else tariff.CG_AMCP2)

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
