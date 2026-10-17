"""t5: the values that were changed by hand.

Manual corrections follow no rule. The rules of t0 to t4 reproduce every other value exactly, so a target value is a
manual correction when it differs from the value the rules calculate. This works for any task with a target file:
it only needs the calculated values and the key and value columns of the file.
"""
import csv
import datetime as dt
import pathlib
from decimal import Decimal, InvalidOperation

# Number of key columns and of scored value columns of every target file (diagnostic columns are not compared)
TARGET_COLUMNS = {
    't0_commission': (2, 1),
    't1_next_due_dates': (2, 2),
    't2_projected_maturity_value': (1, 1),
    't3_surrender_value': (2, 1),
    't4_annual_statement': (2, 6),
}


def parse(text):
    """Read one field of a target file: an ISO date, a whole number, an amount or text.
    Parameters: text (str): Field, e.g. '2026-07-01', '12', '9.45' or 'BL10000013'.
    Returns (object): datetime.date, int, Decimal or str.
    """
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        pass
    try:
        return int(text) if text.isdigit() else Decimal(text)
    except InvalidOperation:
        return text


def single(values):
    """A tuple of one element as the element itself, like the keys and values of the submission.
    Parameters: values (tuple): Parsed fields.
    Returns (object): The only field, or the tuple.
    """
    return values[0] if len(values) == 1 else values


def read_targets(targets_dir, task):
    """Target values of a task, keyed like the results of the submission.
    Parameters: targets_dir (str): Folder with the target files; task (str): Task name, e.g. 't0_commission'.
    Returns (dict): {key: value}, empty if the folder has no file for the task.
    """
    path = pathlib.Path(targets_dir) / f'{task}.csv'
    if not path.exists():
        return {}
    keys, values = TARGET_COLUMNS[task]
    with open(path, encoding='utf-8') as file:
        rows = list(csv.reader(file))[1:]
    return {single(tuple(map(parse, row[:keys]))): single(tuple(map(parse, row[keys:keys + values]))) for row in rows}


def manual_corrections(calculators, targets_dir):
    """All target values that differ from the calculated ones.
    Parameters: calculators (dict): {task: function(target keys) -> {key: calculated value}}; targets_dir (str): Folder
        with the target files of the policies to check.
    Returns (set): {(task, key)} of the values that were changed by hand.
    """
    corrections = set()
    for task, calculate in calculators.items():
        targets = read_targets(targets_dir, task)
        if not targets:
            continue
        calculated = calculate(targets.keys())
        corrections |= {(task, key) for key, value in targets.items()
                        if key in calculated and calculated[key] != value}
    return corrections
