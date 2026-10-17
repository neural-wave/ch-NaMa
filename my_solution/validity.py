"""Inclusive validity lookups; highest overlapping version wins."""
import pandas as pd


def valid_on_date(items, date_column, table, prefix, on, keep_all=False):
    """Attach to each item the row of `table` that is valid on the item's own date.
    A row is valid if VLDFR <= date <= VLDTO; if several are valid, the highest version VRSNR wins.
    Parameters: items (pd.DataFrame): Rows that need a parameter, e.g. premium items; date_column (str): Column of
        `items` with the date that decides, e.g. 'PR_RCVDT'; table (pd.DataFrame): Table with a validity period, e.g.
        NRPOLH or NRCOMR; prefix (str): Two-letter alias of `table`, e.g. 'PH'; on (dict): {column of items: column of
        table} to join on, empty for a table without keys (e.g. NRILLU); keep_all (bool): Keep the items without a valid
        row (with empty table columns), e.g. for agreements.
    Returns (pd.DataFrame): The items joined with their valid row.
    """
    # Find the valid row with the keys and dates only: merging all columns first takes gigabytes for the premiums
    items = items.reset_index(drop=True)
    periods = [column for column in [f'{prefix}_VLDFR', f'{prefix}_VLDTO', f'{prefix}_VRSNR'] if column in table]
    rows = table[list(dict.fromkeys(list(on.values()) + periods))].reset_index(drop=True).reset_index(names='row')
    dates = items[list(on) + [date_column]].reset_index(names='item')
    merged = dates.merge(rows, left_on=list(on), right_on=list(on.values())) if on else dates.merge(rows, how='cross')
    valid = merged[(merged[f'{prefix}_VLDFR'] <= merged[date_column]) & (merged[date_column] <= merged[f'{prefix}_VLDTO'])]
    if f'{prefix}_VRSNR' in valid:
        valid = valid.sort_values(f'{prefix}_VRSNR')
    valid = valid.drop_duplicates('item', keep='last').sort_values('item')

    found = table.iloc[valid.row.to_numpy()].set_axis(valid.item.to_numpy())
    found = found.drop(columns=[column for column in found if column in items])
    if keep_all:
        return items.join(found)
    return items.loc[valid.item.to_numpy()].join(found).reset_index(drop=True)


def valid_on(table, prefix, date, keys):
    """Pick the row valid on `date` per key in a versioned table.
    A row is valid if VLDFR <= date <= VLDTO (both days included). If several rows are valid, the highest version number
    VRSNR wins (see SCHEMA.md).
    Parameters: table (pd.DataFrame): Decoded versioned table, e.g. NRPOLH; prefix (str): Two-letter alias of the table,
        e.g. 'PH'; date (pd.Timestamp): Day on which the rows must be valid; keys (list): Key columns, e.g.
        ['PH_POLNR'].
    Returns (pd.DataFrame): One row per key.
    """
    date = pd.Timestamp(date)
    valid = table[(table[f'{prefix}_VLDFR'] <= date) & (date <= table[f'{prefix}_VLDTO'])]
    return valid.sort_values(f'{prefix}_VRSNR').groupby(keys, as_index=False).last()
