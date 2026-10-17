"""Read the legacy data dictionary and decode CSV chunks, recording invalid dates."""
import pathlib

import pandas as pd

from legacy_formats import DECODERS, invalid_dates


DEFAULT_LEGACY_DIR = pathlib.Path(__file__).resolve().parents[2] / 'legacy'
CHUNK_ROWS = 500_000  # rows decoded at a time: the raw text of a whole large table takes gigabytes


class LegacyReader:
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
