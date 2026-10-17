"""Compare rule applicability with legacy bookings whose amounts are missing.

A booking is a weak label for whether a charge or tax applied, not its amount.
"""
import pandas as pd

from tools.rule_finder import find_rules


def agreement(predicted, booked):
    """Cross-tabulate boolean rule predictions against actual booking presence."""
    return pd.crosstab(pd.Series(list(predicted), name='rule says yes'), pd.Series(list(booked), name='booked'))


def share_agreeing(predicted, booked):
    """Return the agreement fraction of paired rule and booking-presence flags."""
    pairs = list(zip(predicted, booked))
    return sum(rule == legacy for rule, legacy in pairs) / len(pairs)


def explain_disagreement(features, predicted, booked, max_depth=3, min_samples_leaf=3):
    """Explain applicability disagreements using one feature row per case.

    Return the rule-finder's tree text, limited by max_depth and min_samples_leaf.
    """
    disagree = pd.Series([rule != legacy for rule, legacy in zip(predicted, booked)], index=features.index)
    return find_rules(features, disagree, max_depth=max_depth, min_samples_leaf=min_samples_leaf)
