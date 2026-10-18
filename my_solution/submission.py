"""Submission of the Neuron migration challenge.

Each function gets the folder `legacy_dir` with the NR*.csv files and returns the calculated values.
Dates are `datetime.date`, amounts are `decimal.Decimal`. The rules live in one module per task:

- commission.py: t0, commission of the paid premiums
- schedule.py: t1, next due dates and collection dates
- projection.py: t2, value at maturity projected in the offer
- accounting.py (premiums.py, charges.py, market.py): the fund accounting of t3 and t4
- surrender.py: t3, surrender value
- statement.py: t4, annual statement
- outliers.py: t5, values changed by hand
- taxes.py, tax_rules.py: t7, the tax module (surprise challenge)
- rules.py: what all tasks share (parameter lookups, rounding, business calendar)
- legacy_loader.py: reads and decodes the export with the data dictionary NRDICT
"""
import datetime as dt
from decimal import Decimal

from commission import commission
from outliers import manual_corrections
from projection import maturity_values
from rules import extract_date, load
from schedule import next_due_dates
from statement import annual_statements
from surrender import surrender_values
from taxes import tax_results


def t0_commission(legacy_dir) -> dict[tuple[str, int], Decimal]:
    """{(policy_id, due_nr): commission}"""
    return commission(load(legacy_dir))


def t1_next_due_dates(legacy_dir, extract_date: dt.date) -> dict[tuple[str, int], tuple[dt.date, dt.date]]:
    """{(policy_id, n): (due_date, collection_date)} for the due dates after `extract_date`, n = 1, 2, ..."""
    return next_due_dates(load(legacy_dir), extract_date)


def t2_projected_maturity_value(legacy_dir) -> dict[str, Decimal]:
    """{policy_id: maturity_value}"""
    return maturity_values(load(legacy_dir))


def t3_surrender_value(legacy_dir, valuation_dates: list[dt.date]) -> dict[tuple[str, dt.date], Decimal]:
    """{(policy_id, valuation_date): surrender_value}"""
    return surrender_values(load(legacy_dir), valuation_dates)


def t4_annual_statement(legacy_dir) -> dict[tuple[str, int], tuple[Decimal, ...]]:
    """{(policy_id, year): (premiums, entry_charges, admin_fees, management_fees, risk_charges, total_charges)}"""
    return annual_statements(load(legacy_dir))


def t5_outlier_detection(legacy_dir, targets_dir) -> set[tuple[str, object]]:
    """{(task, key)} of the values that were changed by hand.

    `targets_dir` holds the target files (t0 to t4) of the policies to check, in the format of `targets/`. This is
    the only function that may read target files. Example keys: ("t2_projected_maturity_value", "BL10000042"),
    ("t4_annual_statement", ("BL10000042", 2021)).
    """
    data = load(legacy_dir)
    calculators = {
        't0_commission': lambda keys: commission(data),
        't1_next_due_dates': lambda keys: next_due_dates(data, extract_date(data)),
        't2_projected_maturity_value': lambda keys: maturity_values(data),
        't3_surrender_value': lambda keys: surrender_values(data, sorted({day for _, day in keys})),
        't4_annual_statement': lambda keys: annual_statements(data),
    }
    return manual_corrections(calculators, targets_dir)


def t7_tax_payout(legacy_dir) -> dict[tuple[str, int], tuple]:
    """{(policy_id, event_nr): (country, taxable_base, withholding, surcharges, stamp_duty, remittance_date)}"""
    # a row with nothing withheld keeps its zero amounts as text ("0.00"): the same number for the scorer, but never
    # dropped as an all-zero row; no remittance date is an empty text, as in the csv files
    return {key: row if row[5] else tuple(str(v) if isinstance(v, Decimal) and not v else v for v in row[:5]) + ('',)
            for key, row in tax_results(load(legacy_dir))[0].items()}


def t7_tax_annual(legacy_dir) -> dict[tuple[str, int], tuple[Decimal, ...]]:
    """{(policy_id, year): (ch_stp, ch_vst, it_sos, it_bol, de_kst, de_sol, de_kis)}, years with an amount only"""
    return tax_results(load(legacy_dir))[1]
