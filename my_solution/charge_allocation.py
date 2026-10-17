"""Proportional monetary allocation with the remainder on the largest position."""
from decimal import Decimal

from rules import money


def split(total, weights, cobol):
    """
    Split an amount over the positions in proportion to their weights.

    Parameters:
    - total (Decimal): Amount to split.
    - weights (dict): {position: weight}
    - cobol (bool): True for a booking of the COBOL system (truncated amounts).

    Returns:
    - dict: {position: share}, the largest position takes the rounding difference (but never goes below 0).
    """
    weight_sum = sum(weights.values())
    if not total or weight_sum <= 0:
        return {position: Decimal(0) for position in weights}
    shares = {position: money(total * weight / weight_sum, cobol) for position, weight in weights.items()}
    largest = max(weights, key=weights.get)
    shares[largest] = max(shares[largest] + total - sum(shares.values()), Decimal(0))
    return shares
