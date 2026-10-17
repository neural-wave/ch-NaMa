"""Public plotting helpers used by the t6 notebooks.

Chart implementations share the palette and optional file saving in plot_style.
"""
from tools.plot_style import PLOTS, INK, RED, GREEN, GRAY, LIGHT, VARIANT_COLORS, save
from tools.era_plot import share_wrong_by_year, plot_errors_by_era
from tools.statement_plot import plot_statement_waterfall
