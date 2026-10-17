"""t1: the premium due dates of the next year, and the days the money is collected."""
from dateutil.relativedelta import relativedelta

from business_calendar import calendar
from legacy_loader import valid_on
from rules import conversion_date

# Months between two due dates, per premium frequency (single premiums 'E' have no schedule)
FREQUENCY_MONTHS = {'M': 1, 'Q': 3, 'H': 6, 'J': 12}


def due_dates(begin, end, months, conversion, until):
    """
    All due dates of a policy up to `until`, the way Neuron generates them.

    The COBOL system (before the conversion to Neuron NG) added one period to the previous due date, so a day cut
    by a short month stayed cut: 31.01. -> 28.02. -> 28.03. -> ... Neuron NG adds whole periods to an anchor and
    cuts the day only in short months. For converted policies the anchor is the last COBOL due date.

    Parameters:
    - begin (datetime.date): Start date of the policy, the first due date.
    - end (datetime.date): Maturity date, no due date on or after it.
    - months (int): Months between two due dates.
    - conversion (datetime.date): Day of the system conversion.
    - until (datetime.date): Last day of the schedule.

    Returns:
    - list: Due dates as datetime.date.
    """
    dates, due = [], begin
    while due < min(conversion, end):
        dates.append(due)
        due += relativedelta(months=months)

    anchor = dates.pop() if dates else begin
    periods = 0
    while (due := anchor + relativedelta(months=months * periods)) < end and due <= until:
        dates.append(due)
        periods += 1
    return dates


def collection_date(due, payment_method, business_days):
    """
    Day the premium is collected: a direct debit (LS) on the next business day, a bank transfer (UB) on the due date.

    Parameters:
    - due (datetime.date): Due date.
    - payment_method (str): 'LS' or 'UB'.
    - business_days (BusinessCalendar): Business calendar of the export.

    Returns:
    - datetime.date: Collection date.
    """
    return business_days.next_business_day(due) if payment_method == 'LS' else due


def next_due_dates(data, extract_date):
    """
    Due and collection dates after the extract date, up to one year later, of every regular-premium policy in force.

    Parameters:
    - data (LegacyData): Decoded export.
    - extract_date (datetime.date): Day of the export.

    Returns:
    - dict: {(policy number, n): (due date, collection date)} with n = 1, 2, ... after the extract date.
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
