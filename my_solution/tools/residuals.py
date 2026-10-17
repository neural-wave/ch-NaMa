"""Residual analysis: what the differences between calculated and target values say about the missing rule.

- `rounding_modes`: which rounding of the exact values reproduces the targets (half up, cut off, ...).
- `classify_differences`: exact, a rounding step, whole units (typical for values changed by hand), or other.
- `implied_ratios`: the most common ratios target / calculated, matched against known signatures such as a day count
  (days / 360 instead of 1 / 12) or a missing factor.
"""
from collections import Counter
from decimal import Decimal, ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_UP

import pandas as pd

ROUNDING_MODES = {'half up': ROUND_HALF_UP, 'half even': ROUND_HALF_EVEN, 'cut off': ROUND_DOWN,
                  'away from zero': ROUND_UP, 'floor': ROUND_FLOOR, 'ceiling': ROUND_CEILING}


def signatures():
    """
    Known ratios between a value and its usual calculation, e.g. a monthly charge by actual days / 360.

    Returns:
    - dict: {description: ratio}
    """
    known = {'factor 2': 2.0, 'half': 0.5}
    for days in range(28, 32):
        known[f'{days} days / 360 instead of 1/12'] = 12 * days / 360
        known[f'{days} days / 365 instead of 1/12'] = 12 * days / 365
    return known


def rounding_modes(exact_values, targets, step='0.01'):
    """
    Share of the targets each rounding mode reproduces from the exact (unrounded) values.

    Parameters:
    - exact_values (sequence): Unrounded calculated values (Decimal).
    - targets (sequence): Target values (Decimal).
    - step (str): Rounding step, e.g. '0.01' for cents or '0.000001' for fund units.

    Returns:
    - pd.Series: {rounding mode: share of exact matches}, best first.
    """
    pairs = list(zip(exact_values, targets))
    shares = {name: sum(Decimal(value).quantize(Decimal(step), mode) == Decimal(target) for value, target in pairs)
              / len(pairs) for name, mode in ROUNDING_MODES.items()}
    return pd.Series(shares).sort_values(ascending=False)


def classify_differences(calculated, targets, step='0.01'):
    """
    Label every difference target - calculated.

    Parameters:
    - calculated (sequence): Calculated values.
    - targets (sequence): Target values.
    - step (str): Smallest unit of the values, e.g. '0.01'.

    Returns:
    - pd.Series: Count of 'exact', 'one step' (rounding), 'whole units' (often a manual correction) and 'other'.
    """
    labels = Counter()
    for value, target in zip(calculated, targets):
        difference = abs(Decimal(target) - Decimal(value))
        if difference == 0:
            labels['exact'] += 1
        elif difference == Decimal(step):
            labels['one step'] += 1
        elif difference >= 1 and difference % 1 == 0:
            labels['whole units'] += 1
        else:
            labels['other'] += 1
    return pd.Series(labels).reindex(['exact', 'one step', 'whole units', 'other'], fill_value=0)


def implied_ratios(calculated, targets, top=5, decimals=3, tolerance=0.004):
    """
    The most common ratios target / calculated, with the known signature each one matches.

    Parameters:
    - calculated (sequence): Calculated values (non-zero).
    - targets (sequence): Target values.
    - top (int): Number of ratios to report.
    - decimals (int): Decimals the ratios are rounded to before counting.
    - tolerance (float): Largest distance between a ratio and a signature.

    Returns:
    - pd.DataFrame: ratio, number of values, matching signature.
    """
    ratios = Counter(round(float(target) / float(value), decimals) for value, target in zip(calculated, targets)
                     if float(value) != 0 and float(target) != float(value))
    known = signatures()
    rows = []
    for ratio, count in ratios.most_common(top):
        name, signature = min(known.items(), key=lambda item: abs(item[1] - ratio))
        rows.append({'ratio': ratio, 'values': count, 'signature': name if abs(signature - ratio) <= tolerance else ''})
    return pd.DataFrame(rows)
