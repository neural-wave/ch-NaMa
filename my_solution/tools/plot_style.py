"""Shared chart palette and optional saving to the project Plots folder."""
import os
import pathlib


PLOTS = pathlib.Path(__file__).resolve().parents[3] / 'Plots'
INK, RED, GREEN, GRAY, LIGHT = '#16212E', '#D52B1E', '#1F8A70', '#6B7A8F', '#EEF2F6'
VARIANT_COLORS = [RED, GREEN, INK, GRAY]


def save(fig, output_filename):
    """Save a figure in the Plots folder of the project.
    Parameters: fig (matplotlib.figure.Figure): Figure to save; output_filename (str): File name, e.g.
        'errors_by_era.png'; nothing is saved if None.
    """
    if output_filename:
        os.makedirs(PLOTS, exist_ok=True)
        fig.savefig(PLOTS / output_filename, dpi=150, bbox_inches='tight')
