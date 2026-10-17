"""t0 commission submission entry point."""
from decimal import Decimal

from commission import commission
from rules import load


def t0_commission(legacy_dir) -> dict[tuple[str, int], Decimal]:
    """{(policy_id, due_nr): commission}"""
    return commission(load(legacy_dir))
