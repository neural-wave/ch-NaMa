"""Convention search: try every combination of candidate conventions and keep the one that reproduces the targets.

Many details of a legacy calculation are conventions with few possible answers: the rounding mode, the day count, the
date that decides a parameter, the definition of an age, the order of steps. Describe each open question as a named
list of candidates, write one function that calculates with a given choice and counts the exact matches, and the
search ranks all combinations. The candidates below cover the conventions that are common in insurance systems.
"""
from tools.date_conventions import (
    age_last_birthday, age_nearest_birthday, age_days_365, age_days_36525, twelfth, actual_360, actual_365, thirty_360
)
import itertools

import pandas as pd


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
