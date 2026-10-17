"""Loader for the Neuron legacy export (NR*.csv): decoded tables (legacy_tables.py), exact amounts, code texts and
the row of a versioned table valid on a day.
"""
from validity import valid_on
from legacy_formats import OPEN_END, decode_date, to_decimal  # noqa: F401 (OPEN_END, decode_date for the notebooks)
from legacy_tables import LegacyTables


class LegacyData(LegacyTables):
    def exact(self, values, scale=None):
        """Return exact Decimals for a decoded numeric Series.

        Its name selects the NRDICT scale; supply scale for derived columns."""
        if scale is None:
            scale = next(scale for (_, column), (_, scale) in self.dictionary.items() if column == values.name)
        return [to_decimal(value, scale) for value in values]

    def codes(self, domain):
        """Return {code: English text} for a domain such as EVTTP or STATE.

        Some exports put the English text in the German-text column."""
        code_table = self.table('NRCODE')
        rows = code_table[code_table.CD_DOMAIN == domain]

        # The rows of the export have only one text field, so the English text sits in CD_TXTDE
        texts = rows.CD_TXTEN.where(rows.CD_TXTEN != '', rows.CD_TXTDE)
        return dict(zip(rows.CD_CODE, texts))

    def table_names(self):
        """Return sorted NR*.csv table names without their extensions."""
        return sorted(path.stem for path in self.legacy_dir.glob('NR*.csv'))
