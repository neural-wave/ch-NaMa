"""The policies as applied for: contract, main risk, insured person and broker in one row per policy."""

# Mortality table sex by the sex basis of the tariff key; unisex tariffs (U) use the sex of the person
TARIFF_SEX = {'M': '1', 'W': '2'}
# Amounts and rates of the contract that are calculated as exact Decimals
EXACT_COLUMNS = ['PH_PREMI', 'RK_SUMIN', 'RK_LOAD']


def policy_base(data):
    """
    First version of every policy with its main risk, insured person, broker and the parts of the tariff key.

    Parameters:
    - data (LegacyData): Decoded export.

    Returns:
    - pd.DataFrame: One row per policy.
    """
    policies = data.table('NRPOLH').sort_values('PH_VRSNR').drop_duplicates('PH_POLNR')
    policies = policies.merge(data.table('NRRISK').query('RK_RSKNR == 1'), left_on='PH_POLNR', right_on='RK_POLNR')
    policies = policies.merge(data.table('NRPERS'), left_on='RK_PERNR', right_on='PS_PERNR')
    policies = policies.merge(data.table('NRBROK'), left_on='PH_BRKNR', right_on='BR_BRKNR')
    policies = policies.merge(data.table('NRPROD'), left_on='PH_PRDCD', right_on='PD_PRDCD')

    # Tariff key: family (1-2), sex basis (3), generation (4-5), death benefit option (7)
    policies['TARFAM'] = policies.RK_TARKEY.str[:2]
    policies['TARGEN'] = policies.RK_TARKEY.str[3:5]
    policies['OPTION'] = policies.RK_TARKEY.str[6]
    policies['SEX'] = policies.RK_TARKEY.str[2].map(TARIFF_SEX).fillna(policies.PS_SEX)
    for column in EXACT_COLUMNS:
        policies[column] = data.exact(policies[column])
    return policies.reset_index(drop=True)
