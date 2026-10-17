"""Policyholders, residences and birth dates, as Neuron knew them when it processed a payout (late moves did not
count)."""
from collections import defaultdict


class Residence:
    def __init__(self, data):
        """Index the policyholders and their addresses with their validity periods.
        Parameters: data (LegacyData): Decoded export.
        """
        self.holders, self.addresses = defaultdict(list), defaultdict(list)
        for row in data.table('NRHOLD').sort_values('HD_VRSNR').itertuples():
            self.holders[row.HD_POLNR].append((row.HD_VLDFR.date(), row.HD_VLDTO.date(), row.HD_CHGTS, row.HD_PERNR))
        for row in data.table('NRADDR').sort_values('AD_VRSNR').itertuples():
            self.addresses[row.AD_PERNR].append((row.AD_VLDFR.date(), row.AD_VLDTO.date(), row.AD_CHGTS, row))
        self.persons = data.table('NRPERS').set_index('PS_PERNR').PS_BIRTH.to_dict()

    @staticmethod
    def valid(rows, day, known_at=None):
        """The last (highest version) of the rows valid on `day` and entered by `known_at`, or None."""
        valid = [row[3] for row in rows if row[0] <= day <= row[1] and (known_at is None or row[2] <= known_at)]
        return valid[-1] if valid else None

    def holder(self, policy, day, known_at=None):
        """Policyholder of a policy on `day`, as known at `known_at` (today's view if nothing was known yet).
        Parameters: policy (str): Policy number; day (datetime.date): Day; known_at (pd.Timestamp): Processing time.
        Returns (str): Person number.
        """
        rows = self.holders[policy]
        return self.valid(rows, day, known_at) or self.valid(rows, day) or rows[0][3]

    def address(self, policy, day, known_at=None):
        """Address of the policyholder valid on `day`, as known at `known_at` (today's view if nothing was known yet).
        Parameters: policy (str): Policy number; day (datetime.date): Day; known_at (pd.Timestamp): Processing time.
        Returns (namedtuple): Row of NRADDR (country, region, reporting status, church membership).
        """
        rows = self.addresses[self.holder(policy, day, known_at)]
        return self.valid(rows, day, known_at) or self.valid(rows, day) or rows[-1][3]

    def birth(self, policy, day):
        """Birth date of the policyholder on `day`.
        Parameters: policy (str): Policy number; day (datetime.date): Day.
        Returns (datetime.date): Birth date.
        """
        return self.persons[self.holder(policy, day)].date()
