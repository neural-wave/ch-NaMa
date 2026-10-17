"""Reading and decoding the tables of the Neuron legacy export (NR*.csv), chunk by chunk, cached in memory.

Every column is decoded with its type from the data dictionary NRDICT (see legacy_formats.py), so the same code
reads every table. Impossible dates that had to be corrected are recorded in `issues`.
"""
import json
import os
import pathlib

import pandas as pd

from legacy_formats import DECODERS, invalid_dates

DEFAULT_LEGACY_DIR = pathlib.Path(__file__).resolve().parents[2] / 'legacy'
CHUNK_ROWS = 500_000  # rows decoded at a time: the raw text of a whole large table takes gigabytes


class LegacyTables:
    def __init__(self, legacy_dir=DEFAULT_LEGACY_DIR, cache_dir=None):
        """Access to all tables of a Neuron export, decoded and cached in memory.
        Parameters: legacy_dir (str): Folder with the NR*.csv files; cache_dir (str): Optional folder for parquet copies
            of the decoded tables. Reading NRBOOK (8M rows) from parquet takes seconds instead of minutes.
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

    def read_raw(self, name, chunk_rows=None):
        """Read a table as text, exactly as exported.
        Parameters: name (str): Table name, e.g. 'NRPOLH'; chunk_rows (int): Read this many rows at a time (returns an
            iterator of tables); None reads all at once.
        Returns (pd.DataFrame): All columns as str, empty fields as ''.
        """
        path = self.legacy_dir / f'{name}.csv'
        return pd.read_csv(path, sep=';', dtype=str, keep_default_na=False, encoding='utf-8', chunksize=chunk_rows)

    def decode(self, name, raw):
        """Decode every column of a raw table with its type from NRDICT.
        Parameters: name (str): Table name; raw (pd.DataFrame): Table as read by `read_raw`.
        Returns (pd.DataFrame): Decoded table.
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
        """Get a decoded table, from memory, the parquet cache or the csv file.
        Parameters: name (str): Table name, e.g. 'NRPOLH'.
        Returns (pd.DataFrame): Decoded table.
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
            table = pd.concat([self.decode(name, chunk) for chunk in self.read_raw(name, CHUNK_ROWS)], ignore_index=True)
            if cache_path:
                os.makedirs(self.cache_dir, exist_ok=True)
                table.to_parquet(cache_path)
                issues_path.write_text(json.dumps(self.issues[known_issues:]))

        self.tables[name] = table
        return table

    def select(self, name, column, values):
        """The rows of a table whose `column` holds one of `values`, decoded and kept in memory.
        The file is read in chunks and only the selected rows are decoded, so a large table such as NRBOOK (6.8 million
        rows) never sits in memory as a whole.
        Parameters: name (str): Table name, e.g. 'NRBOOK'; column (str): Column to select on, e.g. 'BK_BKTYP'; values
            (list): Values to keep, e.g. ['WDR', 'SUR'].
        Returns (pd.DataFrame): Decoded rows, indexed by their row number in the table (as `table` would give them).
        """
        key = (name, column, tuple(values))
        if key not in self.tables:
            if name in self.tables:
                self.tables[key] = self.tables[name][self.tables[name][column].isin(values)]
            else:
                chunks = self.read_raw(name, CHUNK_ROWS)
                self.tables[key] = self.decode(name, pd.concat(chunk[chunk[column].str.strip().isin(values)]
                                                               for chunk in chunks))
        return self.tables[key]
