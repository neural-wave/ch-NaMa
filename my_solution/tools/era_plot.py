"""Rule errors by year, with the legacy-system conversion marked."""
import matplotlib.pyplot as plt
import pandas as pd

from tools.plot_style import INK, GRAY, LIGHT, VARIANT_COLORS, save


def share_wrong_by_year(years, wrong):
    """Percentage of wrong values per year.
    Parameters: years (sequence): Year of every value, e.g. the application year; wrong (sequence): True where a value
        differs from the target.
    Returns (pd.Series): {year: % wrong}.
    """
    return pd.Series(list(wrong), dtype=float).groupby(list(years)).mean() * 100


def plot_errors_by_era(panels, conversion, output_filename=None):
    """Plot the share of wrong values per year of several rule variants, one panel per task.
    Parameters: panels (list): [(title, years, {variant name: wrong flags})], one entry per panel; conversion
        (pd.Timestamp): Day of the system conversion; the years before are shaded as the COBOL era; output_filename
        (str): File name in the Plots folder.
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
