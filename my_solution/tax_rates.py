"""Versioned tax rates, selected as known at the booking timestamp."""
import datetime as dt
from collections import defaultdict


class TaxRates:
    def __init__(self, data):
        """Index the versioned tax rates by country and tax type.
        Parameters: data (LegacyData): Decoded export.
        """
        table = data.table('NRTAXR')
        thresholds = [None if value != value else value for value in table.TX_THRSH]
        self.rows = defaultdict(list)
        for row, rate, threshold in zip(table.itertuples(), data.exact(table.TX_RATE), thresholds):
            self.rows[(row.TX_CNTRY, row.TX_TAXTP)].append(
                (row.TX_REGIO, row.TX_VLDFR.date(), row.TX_VLDTO.date(), row.TX_VRSNR, row.TX_CHGTS, rate, threshold))

    def changes(self, country, tax, known_at=None):
        """Last days of the rate periods that another period follows, as known at `known_at`."""
        rows = [row for row in self.rows[(country, tax)] if known_at is None or row[4] <= known_at]
        starts = {row[1] for row in rows}
        return sorted({row[2] for row in rows if row[2] + dt.timedelta(days=1) in starts})

    def rate(self, country, tax, day, known_at=None, region=''):
        """Rate of a tax valid on `day`, as known at `known_at`.
        Parameters: country (str): Country code; tax (str): Tax type, e.g. 'KST'; day (datetime.date): Day the rate must
            be valid on; known_at (pd.Timestamp): Processing time of the booking; later versions are not known yet;
            region (str): Region of the residence, for regional rates.
        Returns (tuple): (rate, threshold), (None, None) if the tax has no rate on that day.
        """
        rows = [row for row in self.rows[(country, tax)]
                if row[1] <= day <= row[2] and (known_at is None or row[4] <= known_at) and row[0] in ('', region)]
        if not rows:
            return None, None
        best = max(rows, key=lambda row: (row[0] != '', row[3]))
        return best[5], best[6]
