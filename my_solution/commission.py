"""t0: the commission a broker earns on every premium the customer paid."""
from rules import valid_on_date, money


def premium_types(data):
    """Premium type of every policy: 'L' regular or 'E' single, position 6 of the tariff key of the main risk.
    Parameters: data (LegacyData): Decoded export.
    Returns (dict): {policy number: premium type}.
    """
    main_risks = data.table('NRRISK').query('RK_RSKNR == 1')
    return dict(zip(main_risks.RK_POLNR, main_risks.RK_TARKEY.str[5]))


def commission(data):
    """Commission = received amount x commission rate, rounded half up to the cent.
    Only paid items count: returned (R), open (O) and written-off (W) items earn nothing. The broker is the one of the
    policy version valid on the money date, so a broker change moves the commission from that day on. The rate depends
    on the broker tier and the premium type.
    Parameters: data (LegacyData): Decoded export.
    Returns (dict): {(policy number, instalment number): commission}.
    """
    premiums = data.table('NRPREM').query("PR_STATE == 'P'")
    premiums = valid_on_date(premiums, 'PR_RCVDT', data.table('NRPOLH'), 'PH', {'PR_POLNR': 'PH_POLNR'})

    # Broker tier and premium type select the rate in NRCOMR
    premiums = premiums.merge(data.table('NRBROK'), left_on='PH_BRKNR', right_on='BR_BRKNR')
    premiums['PAYTP'] = premiums.PR_POLNR.map(premium_types(data))
    premiums = valid_on_date(premiums, 'PR_RCVDT', data.table('NRCOMR'), 'CR', {'BR_TIER': 'CR_TIER', 'PAYTP': 'CR_PAYTP'})

    amounts = [money(amount * rate) for amount, rate in zip(data.exact(premiums.PR_AMTRC), data.exact(premiums.CR_RATE))]
    return dict(zip(zip(premiums.PR_POLNR, premiums.PR_DUENR), amounts))
