"""Annual statement charges as a waterfall with their premium shares."""
import matplotlib.pyplot as plt

from tools.plot_style import INK, RED, save


def plot_statement_waterfall(statement, title, output_filename=None):
    """Plot the charges of one annual statement as a waterfall that adds them up to the total charges.
    Parameters: statement (tuple): (premiums, entry, admin, management, risk, total) of one policy and year; title
        (str): Title of the plot, e.g. the policy and year; output_filename (str): File name in the Plots folder.
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
