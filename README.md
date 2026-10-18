# Lifeware Challenge - The Neuron Migration

Neural Wave AI Hackathon. Reverse-engineer the calculation rules of the legacy insurance system Neuron from its data
export, and write them as clear, deterministic Python code.

## Team NAMA

Università della Svizzera italiana (USI), Lugano.

| Name | Role |
|---|---|
| Mohammad Javad Amin | |
| Nava Biglar | |
| Emad Aghajani | |
| Maliheh Ghasemian | |


## Hand-in

- Code: `my_solution/` (entry point `submission.py`, tasks t0 to t5 and the surprise task t7).
- Report (2 pages, limit 3): `report/NAMA_report.pdf`; the long version with every rule: `report/NAMA_report_extended.pdf`.
- Presentation (5 minutes, with speaker notes): `presentation/NAMA_Neuron_Migration.pptx`.
- Video script (2 minutes): `presentation/video_script.md`.

## Status

| Task | Train accuracy | Notes |
|---|---|---|
| t0 Commission | 99.996 % | the 10 misses are manual corrections (not scored officially) |
| t1 Next due dates | 100 % | |
| t2 Projected maturity value | 99.735 % | all 3,019 yearly diagnostics exact; the 8 misses are manual corrections |
| t3 Surrender value | 99.740 % | every premium and charge booking calculated; the 16 misses are manual corrections |
| t4 Annual statement | 99.939 % | the 21 misses are manual corrections |
| t5 Outliers | 55 found | all 38 NREXCP corrections of the train policies plus 17 unlisted ones |
| t7 Tax audit (surprise) | no targets | both examples of the task exact; every tax Neuron booked gets an amount |

Maintainability index (provided local scorer): 83.2, up from 75.3 with identical local predictions and accounting.
Runtime: about 35 seconds for t0-t5 with a peak memory of 1.7 GB; t7 adds 3 seconds,
as it reuses the fund accounting.

## Approach

AI is the detective, not the calculator: the submission is plain, deterministic code, and machine learning and
search only help to find the rules. Every task goes through the same loop:

1. Write the simplest rule from the task description.
2. Mark the values where it differs from the target.
3. Ask the generic tools **why**:

| Question | Tool | Example of a rule it found |
|---|---|---|
| Under which conditions is the rule wrong? | `tools/rule_finder.py` (shallow decision tree) | due dates drift for month-end starts before 2007 |
| On which day did the behaviour change? | `tools/change_points.py` | the COBOL -> Java conversion of 2007-08-11 |
| What do the differences say? | `tools/residuals.py` (implied ratios, rounding modes, difference classes) | COBOL charged days / 360 and cut off the cents; whole-franc differences are manual corrections |
| Which convention is it? | `tools/convention_search.py` (exhaustive search, standard candidates) | the order of the charges; Actual/360 with cut-off rounding |
| No targets: does the rule book what the legacy system booked? | `tools/weak_labels.py` | the Swiss withholding tax needs an objection to reporting and more than CHF 5,000 |
| Which days are business days? | `business_calendar.py` (learned from the price days) | the public holidays of Ticino |

4. Turn the answer into code, check it exactly, repeat until only manual corrections are left.

None of the tools knows anything about insurance, so the loop works for any new target. Notebook 06 shows each tool
rediscovering one of our rules on its own; t7 shows the loop working without any target values (notebook 07).

## Setup

The challenge data is not in this repository. Put `my_solution/` into the `starter_kit/` folder of the challenge
(replacing the template), with the challenge's `legacy/` and `targets/` folders next to `starter_kit/`, then:

```
pip install -r starter_kit/my_solution/requirements.txt
cd starter_kit && python check.py
```

The discovery tools and the notebooks also need `pip install matplotlib scikit-learn jupyter radon`. The notebooks
are stored with their outputs; re-running notebooks 03 to 06 also needs our exploration scripts (`research/`), which
are not part of this hand-in.

## Data Processing

`legacy_loader.py` reads every table of the export with one generic decoder driven by the data dictionary `NRDICT`
(the decoders are in `legacy_formats.py`):

- `C` text: trimmed, `N(s)` numbers: `s` implied decimals, `D` dates: `CYYMMDD` (0 = no date, 9999999 = open end),
  `T` timestamps: `YYYYMMDDHHMMSS`.
- Decoded tables can be cached as parquet in `.cache/` for the tools (NRBOOK: 12 s -> 0.1 s).
- `valid_on` / `valid_on_date` pick the valid row of a versioned or dated table (highest version wins).

Data quality problems found while decoding:

- 10 impossible birth dates (e.g. 31 November), clamped to the month end and logged in `LegacyData.issues`.
- `NRCODE` rows have one text field, so the English text sits in `CD_TXTDE`.
- The smoker flag is `J/N`, not `Y/N`.

## Rules found

**Business calendar** (`business_calendar.py`): Monday to Friday without the Ticino holidays (1.1., 6.1., 19.3., 1.5.,
29.6., 1.8., 15.8., 1.11., 8.12., 25.12., 26.12., Easter Monday, Ascension, Whit Monday, Corpus Christi). It matches
every day with fund prices from 1993 to 2026 exactly.

**t0 Commission** (`commission.py`):
- only paid premium items (`PR_STATE = P`) count; returned, open and written-off items earn nothing;
- the broker is the one of the policy version valid on the money date (`PR_RCVDT`);
- rate from `NRCOMR` by broker tier and premium type (position 6 of the tariff key);
- commission = received amount x rate, rounded half up to the cent.

**t1 Next due dates** (`schedule.py`):
- COBOL (until the system conversion, event 800 on 2007-08-11) added one period to the previous due date, so a
  day cut by a short month stayed cut (31 -> 30 -> 28 -> 28 ...);
- Neuron NG adds whole periods to an anchor (the start date, or the last COBOL due date) and cuts the day only in
  short months;
- no due date on or after maturity; direct debits (`LS`) are collected on the next business day, bank transfers
  (`UB`) on the due date.

**t2 Projected maturity value** (`projection.py`, `risk.py`):
- the offer uses the policy as applied for and the parameters valid on the **application date** (growth rate
  `NRILLU`, charges `NRCHRG`, entry charge `NRENTC`); no agreements;
- every month: premium less entry charge -> admin fee -> management charge (base pot rate, on the value left) ->
  risk charge (on the value left) -> growth by rate / 12;
- risk charge = sum at risk x qx x (1 + loading) x smoker factor / 12; sum at risk by death benefit option (A: 1 % of
  the value, B: sum insured - value, C: sum insured); the age is fixed per policy year;
- Neuron NG: age at the nearest birthday, amounts rounded half up;
- COBOL offers (applied for before 2007-08-11): age = round(days since birth / 365) (leap days ignored), amounts
  truncated to the cent.

**t3 Surrender value and t4 Annual statement** (`accounting.py`, `premiums.py`, `charges.py`, `market.py`,
`surrender.py`, `statement.py`): the whole fund accounting is calculated; only customer orders (switches,
withdrawals, surrenders, death benefits) are taken from `NRBOOK`. All 5,024,847 premium and charge bookings of the
train policies are exact except one manual correction.
- Premium (PRM): per fund received x allocation x (1 - entry charge), allocation, broker tier and entry charge
  (or agreement) on the money date; pot 1 if the money date is within `PD_INIMON` months of the start; units at the
  ask price of the fund's first price day after the money date, FX of the day before.
- The monthly charge run (01:30) sees the units traded before the day; positions are valued at bid with the FX of the
  day and rounded to the cent.
- Admin fee valid on the day (capped at the value) and risk charge are split by value, the largest position takes the
  rounding difference, shares of 0.00 get no booking. Management charge per pot (or AMC agreement) / 12; COBOL:
  x days / 360. The risk charge uses the value after admin fee and management charge.
- Reversed events (900) and technical corrections (990) are ignored; no charges from the day of surrender or death.
- Surrender value: positions at bid on or before the valuation date, penalty by surrender scale and completed policy
  years, none in waiver periods; COBOL truncates value x (1 - rate).
- Annual statement: premiums by money date; entry charges (premium share - amount invested) and charges by trade date.
- Data quality: lowercase currency codes in `NRFXRT` fill gaps and are read as uppercase.

## Files

`my_solution/`:

- Task modules retain their public imports and delegate distinct responsibilities to focused helpers:
  `tax_rates.py`, `residence.py`, `payout_basis.py` and `payout_taxes.py` handle the tax calculation layers;
  `charge_calculation.py` and `charge_allocation.py` handle one monthly charge while `charges.py` advances holdings;
  `legacy_reader.py`, `legacy_numbers.py` and `legacy_dates.py` handle CSV reading and decoding;
  `validity.py`, `offer_terms.py`, `orders.py`, `valuation.py`, `premium_allocation.py`, `premium_schedule.py`
  and `premium_tax.py` hold the corresponding lookup, policy and premium rules. Include all helper files in a submission.
- `submission.py`: the entry point, one function per task.
- `commission.py` (t0), `schedule.py` (t1), `projection.py` (t2), `surrender.py` (t3), `statement.py` (t4),
  `outliers.py` (t5), `taxes.py` with `tax_data.py`, `withholding.py`, `tax_rules.py` and `stamp_duty.py` (t7):
  one module per task.
- `risk.py`: risk charge (sum at risk, entry age, mortality table), shared by t2 and t3.
- `rules.py`: shared building blocks (loading, date-valid lookups, rounding by system era, conversion date).
- `business_calendar.py`: business days and holidays.
- `legacy_loader.py`, `legacy_tables.py`, `legacy_formats.py`: reading and decoding the export, chunk by chunk.
- `charge_parameters.py`, `ledger.py`: parameters of the monthly charges, and what t3, t4 and t7 keep of the
  6.8 million bookings (units per position and day, charges per year).
- `tools/rule_finder.py`, `tools/change_points.py`, `tools/residuals.py`, `tools/convention_search.py`,
  `tools/weak_labels.py`: the generic discovery tools (see Approach).
- `tools/visuals.py` (t6): share of wrong values per year and system era, waterfall of an annual statement.
- `tools/policy_timeline.py`: prints all data of one policy and plots its timeline
  (`python tools/policy_timeline.py BL10000013`).
- `notebooks/01_Data_Exploration.ipynb`: Data Processing, and a walk-through of policy `BL10000013`.
- `notebooks/02_Task_Rules_t0_t1.ipynb`: how the rules of t0 and t1 were found, with the evidence.
- `notebooks/06_Generic_Toolkit.ipynb`: every generic tool rediscovers one of our rules on its own.
- `notebooks/07_Task_t7_Without_Targets.ipynb`: t7 solved with weak labels, the examples and consistency checks.
- `notebooks/05_Visualizations.ipynb` (t6): what happens with the Neuron NG rules for all years, and a statement
  waterfall; the figures are in the notebook and the report.
- `notebooks/04_Task_Rules_t3_t4.ipynb`: how the fund accounting rules were found (teacher forcing, per-booking
  checks), with the remaining manual corrections.
- `notebooks/03_Task_Rules_t2.ipynb`: how the projection rules were found (real risk bookings, convention search,
  rule finder, COBOL age).

`presentation/`: the 5-minute deck with speaker notes and the 2-minute video script. `report/`: the short report and
the extended report.

`check.py`, `scoring.py` (local scoring) and `SCHEMA.md` (description of the export) come with the challenge's
starter kit.
