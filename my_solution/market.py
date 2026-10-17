"""Market data: unit prices of the funds and exchange rates, with the lookups the accounting needs."""
import bisect
from decimal import Decimal


class Market:
    def __init__(self, data):
        """
        Index the prices and exchange rates for fast lookups by date.

        Prices are sometimes restated: the latest publication counts. Exchange rates are CHF per unit of a currency;
        a few rows of the export have lowercase currency codes, they fill gaps and are read as uppercase.

        Parameters:
        - data (LegacyData): Decoded export.

        Returns:
        - None
        """
        prices = data.table('NRFPRC').sort_values('FP_CHGTS').drop_duplicates(['FP_FNDID', 'FP_PRCDT'], keep='last')
        prices = prices.sort_values('FP_PRCDT')
        self.prices = {}
        for fund, rows in prices.groupby('FP_FNDID'):
            self.prices[fund] = ([day.date() for day in rows.FP_PRCDT],
                                 data.exact(rows.FP_BIDPR), data.exact(rows.FP_ASKPR))

        rates = data.table('NRFXRT').assign(FX_CCY=lambda table: table.FX_CCY.str.upper()).sort_values('FX_RATDT')
        self.rates = {currency: ([day.date() for day in rows.FX_RATDT], data.exact(rows.FX_RATE))
                      for currency, rows in rates.groupby('FX_CCY')}
        self.fund_currency = dict(zip(data.table('NRFUND').FD_FNDID, data.table('NRFUND').FD_CCY))

    def price_day_on_or_before(self, fund, day):
        """
        Last day with a price of the fund on or before `day` (the redemption price of a valuation or charge).

        Parameters:
        - fund (str): Fund id.
        - day (datetime.date): Day of the booking or valuation.

        Returns:
        - int: Position of that price in the price lists of the fund.
        """
        return bisect.bisect_right(self.prices[fund][0], day) - 1

    def price_day_after(self, fund, day):
        """
        First day with a price of the fund after `day` (the trade day of money received on `day`).

        Parameters:
        - fund (str): Fund id.
        - day (datetime.date): Money date.

        Returns:
        - int: Position of that price in the price lists of the fund.
        """
        return bisect.bisect_right(self.prices[fund][0], day)

    def bid(self, fund, day):
        """
        Redemption price of the fund: the last bid price on or before `day`.

        Parameters:
        - fund (str): Fund id.
        - day (datetime.date): Day of the booking or valuation.

        Returns:
        - Decimal: Bid price.
        """
        return self.prices[fund][1][self.price_day_on_or_before(fund, day)]

    def purchase(self, fund, money_date):
        """
        Trade day and issue price of money received on `money_date`: the next day the fund has a price.

        Parameters:
        - fund (str): Fund id.
        - money_date (datetime.date): Day the premium arrived.

        Returns:
        - tuple: (trade day, ask price)
        """
        index = self.price_day_after(fund, money_date)
        return self.prices[fund][0][index], self.prices[fund][2][index]

    def rate(self, currency, day):
        """
        CHF per unit of a currency: the last rate on or before `day`.

        Parameters:
        - currency (str): Currency code, e.g. 'EUR'.
        - day (datetime.date): Day of the conversion.

        Returns:
        - Decimal: Exchange rate.
        """
        days, values = self.rates[currency]
        # Before the first rate of a currency (EUR before 1999) its first rate is used
        return values[max(bisect.bisect_right(days, day) - 1, 0)]

    def fund_per_policy(self, fund, policy_currency, day):
        """
        Units of fund currency per unit of policy currency on `day`, cross rate via CHF, not rounded.

        Parameters:
        - fund (str): Fund id.
        - policy_currency (str): Currency of the policy.
        - day (datetime.date): Day of the conversion.

        Returns:
        - Decimal: Exchange rate (1 if the fund is in the policy currency).
        """
        fund_currency = self.fund_currency[fund]
        if fund_currency == policy_currency:
            return Decimal(1)
        return self.rate(policy_currency, day) / self.rate(fund_currency, day)
