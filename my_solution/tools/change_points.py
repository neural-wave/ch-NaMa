"""Change-point finder: the date on which the behaviour of the legacy system changed.

Give it the date of every value (application date, trade date, ...) and a flag that says if the current rule got the
value wrong. It finds the dates where one simple statement, "wrong before this day, right after it" (or the other way
round), explains the most values. A system conversion or a parameter change shows up as the best split.
"""
import pandas as pd


def change_points(dates, wrong, top=3, min_rows=20):
    """
    Find the split dates that best separate wrong from right values.

    Every candidate split predicts the majority (wrong or right) on each side; its score is the share of values this
    one-split rule explains. A sudden change of behaviour on one day gives a score close to 100 %.

    Parameters:
    - dates (sequence): Date of every value.
    - wrong (sequence): True where the value differs from the target.
    - top (int): Number of splits to return.
    - min_rows (int): Fewest values each side of a split must have.

    Returns:
    - pd.DataFrame: last day before and first day after the change, share wrong on both sides, share explained.
    """
    frame = pd.DataFrame({'day': pd.to_datetime(list(dates)), 'wrong': list(wrong)})
    daily = frame.groupby('day').wrong.agg(['sum', 'count'])
    wrong_before, rows_before = daily['sum'].cumsum(), daily['count'].cumsum()
    wrong_after, rows_after = daily['sum'].sum() - wrong_before, daily['count'].sum() - rows_before

    # Values a "majority on each side" rule gets right, for a split after each day
    explained = (pd.concat([wrong_before, rows_before - wrong_before], axis=1).max(axis=1)
                 + pd.concat([wrong_after, rows_after - wrong_after], axis=1).max(axis=1))
    splits = pd.DataFrame({
        'last day before': daily.index,
        'first day after': list(daily.index[1:]) + [pd.NaT],
        'wrong before (%)': (100 * wrong_before / rows_before).round(1).values,
        'wrong after (%)': (100 * wrong_after / rows_after).round(1).values,
        'explained (%)': (100 * explained / daily['count'].sum()).round(2).values,
    })
    splits = splits[(rows_before.values >= min_rows) & (rows_after.values >= min_rows)]
    return splits.sort_values('explained (%)', ascending=False).head(top).reset_index(drop=True)
