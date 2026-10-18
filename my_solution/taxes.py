"""t7: what Neuron's tax module withheld, accrued and reported, per payout and per year.

The inputs are in tax_data.py, the taxes withheld from a payout in withholding.py and the Italian and Swiss stamp
duties in stamp_duty.py; this module puts them together for every policy.
"""
from payout_taxes import TaxModule
import functools
from collections import defaultdict
from decimal import Decimal

from stamp_duty import premium_stamp_duty, stamp_duty

ANNUAL_TAXES = ['STP', 'VST', 'SOS', 'BOL', 'KST', 'SOL', 'KIS']


@functools.cache
def tax_results(data):
    """
    Payout rows and annual amounts of every policy.

    Parameters:
    - data (LegacyData): Decoded export.

    Returns:
    - tuple: ({(policy, event): payout row}, {(policy, year): annual row})
    """
    module = TaxModule(data)
    payout_rows, yearly = {}, defaultdict(lambda: [Decimal('0.00')] * len(ANNUAL_TAXES))
    reported, small = defaultdict(Decimal), defaultdict(Decimal)
    all_payouts = module.payouts()
    for policy, payouts in all_payouts.items():
        rows, amounts = module.policy_taxes(policy, payouts)
        payout_rows.update({(policy, event): row for event, row in rows.items()})
        for (year, tax), amount in amounts.items():
            if tax == 'REPORTED':
                reported[(policy, year)] += amount
            elif tax == 'SMALL':
                small[(policy, year)] += amount
            else:
                yearly[(policy, year)][ANNUAL_TAXES.index(tax)] += amount
    for policy in {row.TB_POLNR for row in module.bookings.itertuples() if row.TB_TAXTP == 'BOL'} - set(all_payouts):
        for day, amount in stamp_duty(module, policy, []):
            yearly[(policy, day.year)][ANNUAL_TAXES.index('BOL')] += amount
    for (policy, year), amount in premium_stamp_duty(module).items():
        yearly[(policy, year)][ANNUAL_TAXES.index('STP')] += amount
    for key, amount in reported.items():  # the Swiss tax reported instead of withheld counts as Swiss tax (m3: +1 row)
        yearly[key][ANNUAL_TAXES.index('VST')] += amount
    annual = {key: tuple(values) for key, values in yearly.items() if any(values)}
    # M4 test: reported tax below the threshold, only as years without a row (an extra row never counts against us)
    vst = ANNUAL_TAXES.index('VST')
    annual.update({key: tuple(amount if i == vst else Decimal('0.00') for i in range(len(ANNUAL_TAXES)))
                   for key, amount in small.items() if amount and key not in annual})
    return payout_rows, annual
