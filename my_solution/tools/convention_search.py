"""Convention search: try every combination of candidate conventions and keep the one that reproduces the targets.

Many details of a legacy calculation are conventions with few possible answers: the rounding mode, the day count, the
date that decides a parameter, the definition of an age, the order of steps. Describe each open question as a named
list of candidates, write one function that calculates with a given choice and counts the exact matches, and the
search ranks all combinations. The candidates below cover the conventions that are common in insurance systems.
"""
import itertools
from decimal import Decimal

import pandas as pd
from dateutil.relativedelta import relativedelta


def age_last_birthday(birth, day):
    """Completed years of age on `day`."""
    return relativedelta(day, birth).years


def age_nearest_birthday(birth, day):
    """Age at the birthday nearest to `day` (completed years six months later)."""
    return relativedelta(day + relativedelta(months=6), birth).years


def age_days_365(birth, day):
    """Days since birth / 365, rounded (leap days ignored, as some old systems did)."""
    return int((day - birth).days / 365 + 0.5)


def age_days_36525(birth, day):
    """Days since birth / 365.25, rounded."""
    return int((day - birth).days / 365.25 + 0.5)


def twelfth(start, end):
    """Monthly share of a yearly rate: 1 / 12 (exact Decimal, like all day counts)."""
    return Decimal(1) / 12


def actual_360(start, end):
    """Actual days / 360."""
    return Decimal((end - start).days) / 360


def actual_365(start, end):
    """Actual days / 365."""
    return Decimal((end - start).days) / 365


def thirty_360(start, end):
    """30 / 360: every month counts 30 days."""
    days = (end.year - start.year) * 360 + (end.month - start.month) * 30 + min(end.day, 30) - min(start.day, 30)
    return Decimal(days) / 360


# Common candidates, to be combined with the open questions of a task
CANDIDATES = {
    'age': [age_last_birthday, age_nearest_birthday, age_days_365, age_days_36525],
    'day count': [twelfth, actual_360, actual_365, thirty_360],
    'rounding': ['half up', 'half even', 'cut off'],
}


def label(choice):
    """
    Readable name of a candidate: the function name, or the value itself.

    Parameters:
    - choice (object): A candidate.

    Returns:
    - str: Its name.
    """
    return getattr(choice, '__name__', str(choice))


def search(options, matches, top=10):
    """
    Rank every combination of candidate conventions by the number of values it reproduces exactly.

    Parameters:
    - options (dict): {open question: [candidates]}
    - matches (callable): matches(choice) -> number of exact values (or a sequence of True/False), where `choice` is
      {open question: candidate}.
    - top (int): Number of combinations to return.

    Returns:
    - pd.DataFrame: One row per combination with its candidates and the number of exact values, best first.
    """
    rows = []
    for combination in itertools.product(*options.values()):
        choice = dict(zip(options, combination))
        result = matches(choice)
        exact = result if isinstance(result, int) else sum(result)
        rows.append({**{question: label(candidate) for question, candidate in choice.items()}, 'exact': exact})
    return pd.DataFrame(rows).sort_values('exact', ascending=False, kind='stable').head(top).reset_index(drop=True)
