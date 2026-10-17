"""Collect and print the linked legacy rows for one policy."""



POLICY_TABLES = {
    'NRPOLH': 'PH_POLNR', 'NRRISK': 'RK_POLNR', 'NRHOLD': 'HD_POLNR', 'NRALLO': 'AL_POLNR',
    'NRAGRE': 'AG_POLNR', 'NRPREM': 'PR_POLNR', 'NREVNT': 'EV_POLNR', 'NRBOOK': 'BK_POLNR',
    'NRTAXB': 'TB_POLNR', 'NREXCP': 'EX_POLNR',
}


def policy_story(data, policy_id):
    """
    Collect the rows of every table that belong to one policy, plus its person, broker and product.

    Parameters:
    - data (LegacyData): Loaded legacy export.
    - policy_id (str): Policy number without blanks, e.g. 'BL10000013'.

    Returns:
    - dict: {table name: pd.DataFrame} with the rows of this policy.
    """
    story = {}
    for name, column in POLICY_TABLES.items():
        table = data.table(name)
        story[name] = table[table[column] == policy_id].reset_index(drop=True)

    # Linked master data: insured person, policyholder, broker and product
    persons = set(story['NRRISK'].RK_PERNR) | set(story['NRHOLD'].HD_PERNR)
    story['NRPERS'] = data.table('NRPERS').query('PS_PERNR in @persons').reset_index(drop=True)
    brokers = set(story['NRPOLH'].PH_BRKNR)
    story['NRBROK'] = data.table('NRBROK').query('BR_BRKNR in @brokers').reset_index(drop=True)
    products = set(story['NRPOLH'].PH_PRDCD)
    story['NRPROD'] = data.table('NRPROD').query('PD_PRDCD in @products').reset_index(drop=True)

    # Readable texts for the event and booking codes
    event_names = data.codes('EVTTP')
    story['NREVNT']['EV_NAME'] = story['NREVNT'].EV_EVTTP.astype(str).map(event_names)
    return story


def print_story(story, max_rows=15):
    """
    Print a short overview of every table of a policy story.

    Parameters:
    - story (dict): Result of `policy_story`.
    - max_rows (int): Maximum number of rows printed per table.

    Returns:
    - None
    """
    for name, table in story.items():
        print(f'\n{name}: {len(table)} rows', 20 * '#')
        if len(table):
            print(table.head(max_rows).to_string())
