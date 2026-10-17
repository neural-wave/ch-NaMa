"""Loader for the Neuron legacy export (NR*.csv): decoded tables (legacy_tables.py), exact amounts, code texts and
the row of a versioned table valid on a day.
"""
import pandas as pd

from legacy_formats import OPEN_END, decode_date, to_decimal  # noqa: F401 (OPEN_END, decode_date for the notebooks)
from legacy_tables import LegacyTables


class LegacyData(LegacyTables):
    def exact(self, values, scale=None):
        """Convert a decoded number column back into exact Decimals, with the scale NRDICT gives the column.
        Parameters: values (pd.Series): Decoded column, e.g. `premiums.PR_AMTRC` (its name finds the scale); scale
            (int): Scale of a derived column that is not in NRDICT.
        Returns (list): Decimals, e.g. [Decimal('315.00'), ...].
        """
        if scale is None:
            scale = next(scale for (_, column), (_, scale) in self.dictionary.items() if column == values.name)
        return [to_decimal(value, scale) for value in values]

    def codes(self, domain):
        """Get the English text of every code of a domain from NRCODE.
        Parameters: domain (str): Code domain, e.g. 'EVTTP' or 'STATE'.
        Returns (dict): {code: English text}.
        """
        code_table = self.table('NRCODE')
        rows = code_table[code_table.CD_DOMAIN == domain]

        # The rows of the export have only one text field, so the English text sits in CD_TXTDE
        texts = rows.CD_TXTEN.where(rows.CD_TXTEN != '', rows.CD_TXTDE)
        return dict(zip(rows.CD_CODE, texts))

    def table_names(self):
        """List the names of all tables in the export.
        Returns (list): Table names, e.g. ['NRADDR', 'NRAGRE', ...].
        """
        return sorted(path.stem for path in self.legacy_dir.glob('NR*.csv'))


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
