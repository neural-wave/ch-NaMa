"""Customer orders, ignored events and the end of monthly charging."""
import pandas as pd


ORDER_TYPES = ['SWO', 'SWI', 'WDR', 'SUR', 'DTH']
REVERSAL, TECHNICAL_CORRECTION = 900, 990
SURRENDERED, DEATH = 60, 70


def ignored_events(data):
    """Events whose bookings do not count: reversed events and technical corrections.
    Parameters: data (LegacyData): Decoded export.
    Returns (set): {(policy number, event number)}.
    """
    events = data.table('NREVNT')
    reversals = events[events.EV_EVTTP == REVERSAL]
    corrections = events[events.EV_EVTTP == TECHNICAL_CORRECTION]
    return set(zip(reversals.EV_POLNR, reversals.EV_REVNR)) | set(zip(corrections.EV_POLNR, corrections.EV_EVTNR))


def order_bookings(data):
    """Bookings of the customer orders, as they are in the export.
    Parameters: data (LegacyData): Decoded export.
    Returns (pd.DataFrame): One row per booking, in the columns of BOOKING_COLUMNS.
    """
    orders = data.select('NRBOOK', 'BK_BKTYP', ORDER_TYPES)
    ignored = ignored_events(data)
    orders = orders[[(policy, event) not in ignored for policy, event in zip(orders.BK_POLNR, orders.BK_EVTNR)]]
    return pd.DataFrame({
        'policy': orders.BK_POLNR.values, 'type': orders.BK_BKTYP.values, 'fund': orders.BK_FNDID.values,
        'pot': orders.BK_POTCD.values, 'money_date': None, 'trade': [day.date() for day in orders.BK_TRDDT],
        'gross': None, 'amount': data.exact(orders.BK_AMTPC), 'units': data.exact(orders.BK_UNITS)})


def end_dates(data):
    """Day a policy ended by surrender or death: from this day on there are no more monthly charges.
    Parameters: data (LegacyData): Decoded export.
    Returns (dict): {policy number: datetime.date}.
    """
    ended = data.table('NRPOLH').query('PH_STATE in [@SURRENDERED, @DEATH]').groupby('PH_POLNR').PH_VLDFR.min()
    return {policy: day.date() for policy, day in ended.items()}
