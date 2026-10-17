"""t2: the value at maturity that the offer projected.

The offer simulates the policy month by month from the start to the maturity date, as one amount and with the
parameters valid on the application date. Every month:

1. a premium that is due is added, less the entry charge;
2. the admin fee, the management charge (base pot rate, on the value left) and the risk charge (on the value left)
   are taken, in this order;
3. the value grows by the illustration rate / 12.

Offers of the COBOL system (applied for before the conversion) truncated every amount to the cent and calculated the
age from the days since birth / 365; Neuron NG rounds half up and takes the age at the nearest birthday.
"""
from offer_terms import EXACT_COLUMNS, offer_terms
from decimal import Decimal

from risk import SMOKER, entry_age, mortality_table, sum_at_risk
from rules import conversion_date, money

# Months between two premiums; a single premium (E) is paid once, at the start
PREMIUM_MONTHS = {'M': 1, 'Q': 3, 'H': 6, 'J': 12, 'E': None}
# Parameters that are calculated as exact Decimals


def project(policy, mortality, conversion):
    """Simulate one offer month by month.
    Parameters: policy (namedtuple): One row of `offer_terms`; mortality (dict): Result of `mortality_table`; conversion
        (pd.Timestamp): Day of the system conversion.
    Returns (list): Value at the end of every policy year, the last one is the value at maturity.
    """
    cobol = policy.PH_APPDT < conversion
    months = (policy.PH_ENDDT.year - policy.PH_BEGDT.year) * 12 + policy.PH_ENDDT.month - policy.PH_BEGDT.month
    premium_every = PREMIUM_MONTHS[policy.PH_FREQ] or months
    net_premium = money(policy.PH_PREMI * (1 - policy.EC_RATE), cobol)
    smoker_factor = policy.CG_SMKFAC if policy.PS_SMOKE == SMOKER else 1
    age = entry_age(policy.PS_BIRTH, policy.PH_BEGDT, cobol)

    value, values = Decimal(0), []
    for month in range(months):
        if month % premium_every == 0:
            value += net_premium
        value -= money(policy.CG_ADMFEE, cobol)
        value -= money(value * policy.CG_AMCP2 / 12, cobol)
        qx = mortality[(policy.CG_MORTTB, policy.SEX, age + month // 12)]
        risk = sum_at_risk(policy.OPTION, value, policy.RK_SUMIN) * qx * (1 + policy.RK_LOAD) * smoker_factor / 12
        value -= money(risk, cobol)
        value = money(value * (1 + policy.IL_RATE / 12), cobol)
        if (month + 1) % 12 == 0 or month + 1 == months:
            values.append(value)
    return values


def projected_values(data):
    """Projected values at the end of every policy year, for every policy.
    Parameters: data (LegacyData): Decoded export.
    Returns (dict): {policy number: [value at the end of policy year 1, 2, ...]}.
    """
    mortality, conversion = mortality_table(data), conversion_date(data)
    return {policy.PH_POLNR: project(policy, mortality, conversion) for policy in offer_terms(data).itertuples()}


def maturity_values(data):
    """Projected value at maturity of every policy.
    Parameters: data (LegacyData): Decoded export.
    Returns (dict): {policy number: value at maturity}.
    """
    return {policy: values[-1] for policy, values in projected_values(data).items()}
