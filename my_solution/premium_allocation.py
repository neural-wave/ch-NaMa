"""Paid premiums joined to allocation, broker tier and entry-charge agreements."""
from rules import valid_on_date


PAID = 'P'


def allocated_premiums(data):
    """One row per paid premium and fund, with the allocation share and the entry charge rate of the money date.
    Parameters: data (LegacyData): Decoded export.
    Returns (pd.DataFrame): Premium items joined with their allocation, broker tier and entry charge rate.
    """
    # Only the columns the bookings need: 550,000 rows with every column of six tables take gigabytes
    premiums = data.table('NRPREM').query('PR_STATE == @PAID')[['PR_POLNR', 'PR_DUENR', 'PR_RCVDT', 'PR_AMTRC']]

    # The allocation version valid on the money date, with all its funds
    allocated = premiums.merge(data.table('NRALLO'), left_on='PR_POLNR', right_on='AL_POLNR')
    allocated = allocated[(allocated.AL_VLDFR <= allocated.PR_RCVDT) & (allocated.PR_RCVDT <= allocated.AL_VLDTO)]
    newest = allocated.groupby(['PR_POLNR', 'PR_DUENR']).AL_VRSNR.transform('max')
    allocated = allocated[allocated.AL_VRSNR == newest]

    # Entry charge of the broker tier, replaced by an individual agreement while one is valid
    versions = data.table('NRPOLH')[['PH_POLNR', 'PH_VRSNR', 'PH_VLDFR', 'PH_VLDTO', 'PH_BRKNR']]
    allocated = valid_on_date(allocated, 'PR_RCVDT', versions, 'PH', {'PR_POLNR': 'PH_POLNR'})
    allocated = allocated.merge(data.table('NRBROK'), left_on='PH_BRKNR', right_on='BR_BRKNR')
    allocated = valid_on_date(allocated, 'PR_RCVDT', data.table('NRENTC'), 'EC', {'BR_TIER': 'EC_TIER'})
    agreements = data.table('NRAGRE').query("AG_FEETP == 'ENT'")
    allocated = valid_on_date(allocated, 'PR_RCVDT', agreements, 'AG', {'PR_POLNR': 'AG_POLNR'}, keep_all=True)
    allocated['ENTRY_RATE'] = allocated.AG_RATE.fillna(allocated.EC_RATE)
    return allocated
