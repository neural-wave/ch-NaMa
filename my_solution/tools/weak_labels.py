"""Weak labels: learn rules from what the legacy system booked, when there are no target values.

Legacy exports often keep the bookings of a calculation without their amounts (NRBOOK, NRTAXB). That a booking exists
is a label too: the legacy system decided that a fee, a tax or a charge applies. A candidate rule predicts when it
applies (for example "a tax is due when the gain is positive"); comparing the prediction with the existing bookings
shows how well it fits, and the rule finder explains the cases where it does not.
"""
import pandas as pd

from tools.rule_finder import find_rules


def agreement(predicted, booked):
    """
    How often a candidate rule agrees with the legacy bookings.

    Parameters:
    - predicted (sequence): True where the rule says the booking applies.
    - booked (sequence): True where the legacy system made the booking.

    Returns:
    - pd.DataFrame: Counts of the cases, rule against bookings.
    """
    return pd.crosstab(pd.Series(list(predicted), name='rule says yes'), pd.Series(list(booked), name='booked'))


def share_agreeing(predicted, booked):
    """
    Share of the cases where a candidate rule agrees with the legacy bookings.

    Parameters:
    - predicted (sequence): True where the rule says the booking applies.
    - booked (sequence): True where the legacy system made the booking.

    Returns:
    - float: Share of agreement, from 0 to 1.
    """
    pairs = list(zip(predicted, booked))
    return sum(rule == legacy for rule, legacy in pairs) / len(pairs)


def explain_disagreement(features, predicted, booked, max_depth=3, min_samples_leaf=3):
    """
    Let the rule finder explain where a candidate rule and the legacy bookings disagree.

    Parameters:
    - features (pd.DataFrame): Candidate explanations, one row per case.
    - predicted (sequence): True where the rule says the booking applies.
    - booked (sequence): True where the legacy system made the booking.
    - max_depth (int): Depth of the tree.
    - min_samples_leaf (int): Smallest group a condition may describe.

    Returns:
    - str: Conditions of the disagreements, as printed by the rule finder.
    """
    disagree = pd.Series([rule != legacy for rule, legacy in zip(predicted, booked)], index=features.index)
    return find_rules(features, disagree, max_depth=max_depth, min_samples_leaf=min_samples_leaf)
