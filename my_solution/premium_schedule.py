"""COBOL/Neuron due-date recurrence and payment-method collection rules."""
from dateutil.relativedelta import relativedelta


def due_dates(begin, end, months, conversion, until):
    """All due dates of a policy up to `until`, the way Neuron generates them.
    The COBOL system (before the conversion to Neuron NG) added one period to the previous due date, so a day cut by a
    short month stayed cut: 31.01. -> 28.02. -> 28.03. -> ... Neuron NG adds whole periods to an anchor and cuts the day
    only in short months. For converted policies the anchor is the last COBOL due date.
    Parameters: begin (datetime.date): Start date of the policy, the first due date; end (datetime.date): Maturity date,
        no due date on or after it; months (int): Months between two due dates; conversion (datetime.date): Day of the
        system conversion; until (datetime.date): Last day of the schedule.
    Returns (list): Due dates as datetime.date.
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
    """Day the premium is collected: a direct debit (LS) on the next business day, a bank transfer (UB) on the due date.
    Parameters: due (datetime.date): Due date; payment_method (str): 'LS' or 'UB'; business_days (BusinessCalendar):
        Business calendar of the export.
    Returns (datetime.date): Collection date.
    """
    return business_days.next_business_day(due) if payment_method == 'LS' else due
