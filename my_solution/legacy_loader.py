"""Loader for the Neuron legacy export (NR*.csv).

Every column is decoded with its type from the data dictionary NRDICT (see legacy_formats.py), so the same code
reads every table. Impossible dates that had to be corrected are recorded in `LegacyData.issues`.
"""
import json
import os
import pathlib

import pandas as pd

from legacy_formats import DECODERS, OPEN_END, decode_date, invalid_dates, to_decimal  # noqa: F401

DEFAULT_LEGACY_DIR = pathlib.Path(__file__).resolve().parents[2] / 'legacy'


class LegacyData:
    def __init__(self, legacy_dir=DEFAULT_LEGACY_DIR, cache_dir=None):
        """
        Access to all tables of a Neuron export, decoded and cached in memory.

        Parameters:
        - legacy_dir (str): Folder with the NR*.csv files.
        - cache_dir (str): Optional folder for parquet copies of the decoded tables.
          Reading NRBOOK (8M rows) from parquet takes seconds instead of minutes.

        Returns:
        - None
        """
        self.legacy_dir = pathlib.Path(legacy_dir)
        self.cache_dir = pathlib.Path(cache_dir) if cache_dir else None
        self.tables = {}
        self.issues = []

        # The data dictionary describes every column, including its own
        raw_dict = self.read_raw('NRDICT')
        self.dictionary = {
            (row.DC_TABLE.strip(), row.DC_COLUMN.strip()): (row.DC_TYPE.strip(), int(row.DC_SCALE or 0))
            for row in raw_dict.itertuples()
        }

    def read_raw(self, name):
        """
        Read a table as text, exactly as exported.

        Parameters:
        - name (str): Table name, e.g. 'NRPOLH'.

        Returns:
        - pd.DataFrame: All columns as str, empty fields as ''.
        """
        path = self.legacy_dir / f'{name}.csv'
        return pd.read_csv(path, sep=';', dtype=str, keep_default_na=False, encoding='utf-8')

    def decode(self, name, raw):
        """
        Decode every column of a raw table with its type from NRDICT.

        Parameters:
        - name (str): Table name.
        - raw (pd.DataFrame): Table as read by `read_raw`.

        Returns:
        - pd.DataFrame: Decoded table.
        """
        table = pd.DataFrame(index=raw.index)
        for column in raw.columns:
            kind, scale = self.dictionary[(name, column)]
            table[column] = DECODERS[kind](raw[column], scale)

            # Keep a record of every impossible date that was clamped
            if kind == 'D':
                for row, value in invalid_dates(raw[column]).items():
                    self.issues.append({'table': name, 'column': column, 'row': row, 'raw': value})
        return table

    def table(self, name):
        """
        Get a decoded table, from memory, the parquet cache or the csv file.

        Parameters:
        - name (str): Table name, e.g. 'NRPOLH'.

        Returns:
        - pd.DataFrame: Decoded table.
        """
        if name in self.tables:
            return self.tables[name]

        cache_path = self.cache_dir / f'{name}.parquet' if self.cache_dir else None
        issues_path = self.cache_dir / f'{name}.issues.json' if self.cache_dir else None
        if cache_path and cache_path.exists():
            table = pd.read_parquet(cache_path)
            self.issues.extend(json.loads(issues_path.read_text()))
        else:
            known_issues = len(self.issues)
            table = self.decode(name, self.read_raw(name))
            if cache_path:
                os.makedirs(self.cache_dir, exist_ok=True)
                table.to_parquet(cache_path)
                issues_path.write_text(json.dumps(self.issues[known_issues:]))

        self.tables[name] = table
        return table

    def exact(self, values, scale=None):
        """
        Convert a decoded number column back into exact Decimals, with the scale NRDICT gives the column.

        Parameters:
        - values (pd.Series): Decoded column, e.g. `premiums.PR_AMTRC` (its name finds the scale).
        - scale (int): Scale of a derived column that is not in NRDICT.

        Returns:
        - list: Decimals, e.g. [Decimal('315.00'), ...].
        """
        if scale is None:
            scale = next(scale for (_, column), (_, scale) in self.dictionary.items() if column == values.name)
        return [to_decimal(value, scale) for value in values]

    def codes(self, domain):
        """
        Get the English text of every code of a domain from NRCODE.

        Parameters:
        - domain (str): Code domain, e.g. 'EVTTP' or 'STATE'.

        Returns:
        - dict: {code: English text}
        """
        code_table = self.table('NRCODE')
        rows = code_table[code_table.CD_DOMAIN == domain]

        # The rows of the export have only one text field, so the English text sits in CD_TXTDE
        texts = rows.CD_TXTEN.where(rows.CD_TXTEN != '', rows.CD_TXTDE)
        return dict(zip(rows.CD_CODE, texts))

    def table_names(self):
        """
        List the names of all tables in the export.

        Returns:
        - list: Table names, e.g. ['NRADDR', 'NRAGRE', ...].
        """
        return sorted(path.stem for path in self.legacy_dir.glob('NR*.csv'))


def valid_on(table, prefix, date, keys):
    """
    Pick the row valid on `date` per key in a versioned table.

    A row is valid if VLDFR <= date <= VLDTO (both days included). If several rows are valid,
    the highest version number VRSNR wins (see SCHEMA.md).

    Parameters:
    - table (pd.DataFrame): Decoded versioned table, e.g. NRPOLH.
    - prefix (str): Two-letter alias of the table, e.g. 'PH'.
    - date (pd.Timestamp): Day on which the rows must be valid.
    - keys (list): Key columns, e.g. ['PH_POLNR'].

    Returns:
    - pd.DataFrame: One row per key.
    """
    date = pd.Timestamp(date)
    valid = table[(table[f'{prefix}_VLDFR'] <= date) & (date <= table[f'{prefix}_VLDTO'])]
    return valid.sort_values(f'{prefix}_VRSNR').groupby(keys, as_index=False).last()
