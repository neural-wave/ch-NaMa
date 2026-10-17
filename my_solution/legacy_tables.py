"""Reading and decoding the tables of the Neuron legacy export (NR*.csv), chunk by chunk, cached in memory.

Every column is decoded with its type from the data dictionary NRDICT (see legacy_formats.py), so the same code
reads every table. Impossible dates that had to be corrected are recorded in `issues`.
"""
from legacy_reader import CHUNK_ROWS, DEFAULT_LEGACY_DIR, LegacyReader
import json
import os

import pandas as pd



class LegacyTables(LegacyReader):
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
