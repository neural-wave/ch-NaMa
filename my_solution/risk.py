"""Risk charge: the monthly price of the death benefit above the value of the policy.

risk charge = sum at risk x death probability qx(age) x (1 + medical loading) x smoker factor / 12
"""
from decimal import Decimal

from dateutil.relativedelta import relativedelta

SMOKER = 'J'


def sum_at_risk(option, value, sum_insured):
    """Part of the death benefit above the value, by the death benefit option (position 7 of the tariff key).
    Parameters: option (str): 'A' 101 % of the value, 'B' the higher of sum insured and value, 'C' value plus sum
        insured; value (Decimal): Current value; sum_insured (Decimal): Sum insured of the main risk.
    Returns (Decimal): Sum at risk.
    """
    if option == 'A':
        return value * Decimal('0.01')
    if option == 'B':
        return max(sum_insured - value, Decimal(0))
    return sum_insured


def entry_age(birth, begin, cobol):
    """Age of the insured person at the start; it grows by one every policy year.
    Parameters: birth (pd.Timestamp): Birth date; begin (pd.Timestamp): Start date of the policy; cobol (bool): True for
        an offer of the COBOL system.
    Returns (int): COBOL: days since birth / 365, rounded; Neuron NG: age at the nearest birthday.
    """
    if cobol:
        return int((begin - birth).days / 365 + 0.5)
    return relativedelta(begin + relativedelta(months=6), birth).years


def mortality_table(data):
    """Death probabilities by mortality table, sex and age.
    Parameters: data (LegacyData): Decoded export.
    Returns (dict): {(table, sex, age): qx}.
    """
    table = data.table('NRMORT')
    return dict(zip(zip(table.MO_TABID, table.MO_SEX, table.MO_AGE), data.exact(table.MO_QX)))
