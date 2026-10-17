"""t1: the premium due dates of the next year, and the days the money is collected."""
from premium_schedule import due_dates, collection_date
from dateutil.relativedelta import relativedelta

from business_calendar import calendar
from legacy_loader import valid_on
from rules import conversion_date

# Months between two due dates, per premium frequency (single premiums 'E' have no schedule)
FREQUENCY_MONTHS = {'M': 1, 'Q': 3, 'H': 6, 'J': 12}


def next_due_dates(data, extract_date):
    """Due and collection dates after the extract date, up to one year later, of every regular-premium policy in force.
    Parameters: data (LegacyData): Decoded export; extract_date (datetime.date): Day of the export.
    Returns (dict): {(policy number, n): (due date, collection date)} with n = 1, 2, ... after the extract date.
    """
    until = extract_date + relativedelta(years=1)
    conversion, business_days = conversion_date(data).date(), calendar(data)

    # Policy version valid on the extract date: in force (state 10) and paying regular premiums
    policies = valid_on(data.table('NRPOLH'), 'PH', extract_date, ['PH_POLNR'])
    policies = policies[(policies.PH_STATE == 10) & policies.PH_FREQ.isin(list(FREQUENCY_MONTHS))]

    result = {}
    for policy in policies.itertuples():
        dates = due_dates(policy.PH_BEGDT.date(), policy.PH_ENDDT.date(), FREQUENCY_MONTHS[policy.PH_FREQ],
                          conversion, until)
        future = [due for due in dates if due > extract_date]
        for n, due in enumerate(future, start=1):
            result[(policy.PH_POLNR, n)] = (due, collection_date(due, policy.PH_PAYMT, business_days))
    return result
