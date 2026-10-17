"""Parameters of the monthly charges: the tariff valid on a day, management charge agreements and mortality."""
from collections import defaultdict

from risk import mortality_table


class ChargeParameters:
    def __init__(self, data, market, conversion):
        """Parameters of the monthly charges: tariff charges by tariff family and generation, AMC agreements, mortality.
        Parameters: data (LegacyData): Decoded export; market (Market): Prices and exchange rates; conversion
            (datetime.date): Day of the system conversion.
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
        """Charges of the tariff of the policy valid on `day`.
        Parameters: policy (namedtuple): Row of `policy_base`; day (datetime.date): Charge day.
        Returns (namedtuple): Row of NRCHRG.
        """
        return next(row for start, end, row in self.tariffs[(policy.TARFAM, policy.TARGEN)] if start <= day <= end)

    def management_rate(self, policy, pot, tariff, day):
        """Yearly management charge of a pot: an agreement valid on `day` replaces the rate of the tariff.
        Parameters: policy (namedtuple): Row of `policy_base`; pot (str): '1' initial units, '2' base units; tariff
            (namedtuple): Row of NRCHRG valid on `day`; day (datetime.date): Charge day.
        Returns (Decimal): Yearly rate.
        """
        agreed = [rate for start, end, rate in self.agreements[policy.PH_POLNR] if start <= day <= end]
        return agreed[-1] if agreed else (tariff.CG_AMCP1 if pot == '1' else tariff.CG_AMCP2)
