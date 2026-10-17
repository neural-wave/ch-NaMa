"""Visualisations (t6): pictures that make Neuron's hidden rules visible.

- `plot_errors_by_era`: share of wrong values per year for several rule variants, with the COBOL era shaded.
  A rule that is right in one era and wrong in the other shows up as a step at the system conversion.
- `plot_statement_waterfall`: the charges of an annual statement as a waterfall, added up to the total charges.
"""
import os
import pathlib

import matplotlib.pyplot as plt
import pandas as pd

PLOTS = pathlib.Path(__file__).resolve().parents[3] / 'Plots'
INK, RED, GREEN, GRAY, LIGHT = '#16212E', '#D52B1E', '#1F8A70', '#6B7A8F', '#EEF2F6'
VARIANT_COLORS = [RED, GREEN, INK, GRAY]


def save(fig, output_filename):
    """
    Save a figure in the Plots folder of the project.

    Parameters:
    - fig (matplotlib.figure.Figure): Figure to save.
    - output_filename (str): File name, e.g. 'errors_by_era.png'; nothing is saved if None.

    Returns:
    - None
    """
    if output_filename:
        os.makedirs(PLOTS, exist_ok=True)
        fig.savefig(PLOTS / output_filename, dpi=150, bbox_inches='tight')


def share_wrong_by_year(years, wrong):
    """
    Percentage of wrong values per year.

    Parameters:
    - years (sequence): Year of every value, e.g. the application year.
    - wrong (sequence): True where a value differs from the target.

    Returns:
    - pd.Series: {year: % wrong}
    """
    return pd.Series(list(wrong), dtype=float).groupby(list(years)).mean() * 100


def plot_errors_by_era(panels, conversion, output_filename=None):
    """
    Plot the share of wrong values per year of several rule variants, one panel per task.

    Parameters:
    - panels (list): [(title, years, {variant name: wrong flags})], one entry per panel.
    - conversion (pd.Timestamp): Day of the system conversion; the years before are shaded as the COBOL era.
    - output_filename (str): File name in the Plots folder.

    Returns:
    - None
    """
    fig, axes = plt.subplots(len(panels), 1, figsize=(12, 3.3 * len(panels)), sharex=True, squeeze=False)
    conversion_year = conversion.year + (conversion.dayofyear - 1) / 365.25
    for ax, (title, years, variants) in zip(axes[:, 0], panels):
        ax.axvspan(min(years) - 0.5, conversion_year, color=LIGHT, zorder=0)
        ax.axvline(conversion_year, color=GRAY, linestyle='--', linewidth=1)
        ax.text(conversion_year, 103, f'  conversion {conversion.date()}', color=GRAY, fontsize=9, va='bottom')
        ax.text(min(years), 103, 'COBOL era', color=GRAY, fontsize=9, va='bottom')
        for (name, wrong), color in zip(variants.items(), VARIANT_COLORS):
            share = share_wrong_by_year(years, wrong)
            ax.plot(share.index, share.values, marker='o', markersize=4, color=color, label=name)
        ax.set_title(title, loc='left', fontsize=12, color=INK)
        ax.set_ylabel('% wrong')
        ax.set_ylim(-3, 112)
        ax.grid(alpha=0.3)
        ax.legend(loc='center right', frameon=False)
    axes[-1, 0].set_xlabel('Year')
    fig.tight_layout()
    save(fig, output_filename)
    plt.show()


def plot_statement_waterfall(statement, title, output_filename=None):
    """
    Plot the charges of one annual statement as a waterfall that adds them up to the total charges.

    Parameters:
    - statement (tuple): (premiums, entry, admin, management, risk, total) of one policy and year.
    - title (str): Title of the plot, e.g. the policy and year.
    - output_filename (str): File name in the Plots folder.

    Returns:
    - None
    """
    premiums, entry, admin, management, risk, total = map(float, statement)
    steps = [('Entry charges', entry), ('Admin fees', admin), ('Management fees', management), ('Risk charges', risk)]
    fig, ax = plt.subplots(figsize=(10, 4.5))

    # Every charge starts where the previous one ended; the last bar is the total
    level = 0
    for name, charge in steps:
        ax.bar(name, charge, bottom=level, color=RED)
        ax.text(name, level + charge, f'{charge:,.2f}\n{charge / premiums:.1%}', ha='center', va='bottom', fontsize=10)
        level += charge
    ax.bar('Total charges', total, color=INK)
    ax.text('Total charges', total, f'{total:,.2f}\n{total / premiums:.1%}', ha='center', va='bottom', fontsize=10)

    ax.set_title(f'{title}: charges on {premiums:,.2f} of premiums (share of the premiums below each value)',
                 loc='left', fontsize=12, color=INK)
    ax.set_ylabel('Amount')
    ax.set_ylim(0, total * 1.2)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    save(fig, output_filename)
    plt.show()
