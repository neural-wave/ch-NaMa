"""Original policy terms and tariff parameters valid at application."""
from policies import policy_base
from rules import valid_on_date


EXACT_COLUMNS = ['IL_RATE', 'CG_ADMFEE', 'CG_AMCP2', 'CG_SMKFAC', 'EC_RATE']


def offer_terms(data):
    """Everything an offer was calculated with: the policy as applied for and the parameters of its application date.
    Parameters: data (LegacyData): Decoded export.
    Returns (pd.DataFrame): One row per policy.
    """
    policies = policy_base(data)
    policies = valid_on_date(policies, 'PH_APPDT', data.table('NRILLU'), 'IL', {})
    policies = valid_on_date(policies, 'PH_APPDT', data.table('NRCHRG'), 'CG',
                             {'TARFAM': 'CG_TARFAM', 'TARGEN': 'CG_TARGEN'})
    policies = valid_on_date(policies, 'PH_APPDT', data.table('NRENTC'), 'EC', {'BR_TIER': 'EC_TIER'})
    for column in EXACT_COLUMNS:
        policies[column] = data.exact(policies[column])
    return policies
