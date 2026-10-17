"""t3: surrender value of every policy on the valuation dates.

The units of every fund and pot are valued at the redemption (bid) price on or before the valuation date, converted
into the policy currency and rounded to the cent. The surrender penalty depends on the surrender scale of the product
and the completed policy years; there is no penalty in a waiver period. Surrendered policies and policies of insured
persons who died are worth 0.
"""
from dateutil.relativedelta import relativedelta

from accounting import bookings
from legacy_loader import valid_on
from market import Market
from policies import policy_base
from rules import conversion_date, money

ENDED = [60, 70]


def penalty_rate(data, scale, years, day):
    """
    Surrender penalty of a surrender scale after `years` completed policy years; none in a waiver period.

    Parameters:
    - data (LegacyData): Decoded export.
    - scale (int): Surrender scale of the product (PD_SRPSCL).
    - years (int): Completed policy years.
    - day (datetime.date): Valuation date.

    Returns:
    - Decimal: Penalty rate (0 if the scale has no row for these years).
    """
    waivers = data.table('NRWAIV')
    if ((waivers.WV_VLDFR.dt.date <= day) & (day <= waivers.WV_VLDTO.dt.date)).any():
        return 0
    rates = data.table('NRSURR')
    rates = rates[(rates.SR_SCALE == scale) & (rates.SR_YEAR == years)]
    return data.exact(rates.SR_RATE)[0] if len(rates) else 0


def policy_values(data, market, day):
    """
    Value of the units of every policy on `day`, each fund and pot rounded to the cent.

    Parameters:
    - data (LegacyData): Decoded export.
    - market (Market): Prices and exchange rates.
    - day (datetime.date): Valuation date.

    Returns:
    - dict: {policy number: value}
    """
    cobol = day < conversion_date(data).date()
    currency = dict(zip(data.table('NRPOLH').PH_POLNR, data.table('NRPOLH').PH_CCY))
    held = bookings(data)
    held = held[held.trade <= day].groupby(['policy', 'fund', 'pot']).units.sum()
    values = {}
    for (policy, fund, _), units in held.items():
        rate = market.fund_per_policy(fund, currency[policy], day)
        values[policy] = values.get(policy, 0) + money(units * market.bid(fund, day) / rate, cobol)
    return values


def surrender_values(data, valuation_dates):
    """
    Surrender value of every policy that started on or before each valuation date.

    Parameters:
    - data (LegacyData): Decoded export.
    - valuation_dates (list): Valuation dates as datetime.date.

    Returns:
    - dict: {(policy number, valuation date): surrender value}
    """
    market, policies = Market(data), policy_base(data)
    result = {}
    for day in valuation_dates:
        cobol = day < conversion_date(data).date()
        values = policy_values(data, market, day)
        states = valid_on(data.table('NRPOLH'), 'PH', day, ['PH_POLNR']).set_index('PH_POLNR').PH_STATE
        for policy in policies[policies.PH_BEGDT.dt.date <= day].itertuples():
            value = values.get(policy.PH_POLNR, 0) if states.get(policy.PH_POLNR) not in ENDED else 0
            years = relativedelta(day, policy.PH_BEGDT.date()).years
            rate = penalty_rate(data, policy.PD_SRPSCL, years, day)
            result[(policy.PH_POLNR, day)] = max(money(value * (1 - rate), cobol), 0) if value else 0
    return result
