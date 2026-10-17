"""Plot policy versions, premium items and business events."""
import matplotlib.pyplot as plt
import pandas as pd

from tools.plot_paths import get_path


PREMIUM_COLORS = {'P': 'tab:green', 'R': 'tab:red', 'O': 'tab:orange', 'W': 'tab:gray'}


def plot_timeline(story, output_filename=None):
    """
    Plot the timeline of one policy: policy versions, premium items and business events.

    Parameters:
    - story (dict): Result of `policy_story`.
    - output_filename (str): Filename in the Plots folder, default 'timeline_<policy>.png'.

    Returns:
    - None
    """
    policy_id = story['NRPOLH'].PH_POLNR.iloc[0]
    fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(16, 9), sharex=True)
    fig.suptitle(f'Policy {policy_id}', fontsize=16)

    # Policy versions: one bar per version, labelled with its state
    versions = story['NRPOLH']
    end = versions.PH_VLDTO.clip(upper=pd.Timestamp('2026-06-30'))
    for row, version_end in zip(versions.itertuples(), end):
        axes[0].barh(0, version_end - row.PH_VLDFR, left=row.PH_VLDFR, height=0.5, edgecolor='black')
        axes[0].text(row.PH_VLDFR, 0, f' v{row.PH_VRSNR} state {row.PH_STATE}', fontsize=9, va='center')
    axes[0].set_yticks([])
    axes[0].set_title('Policy versions (NRPOLH)')

    # Premium items: due date against received amount, colored by item state
    premiums = story['NRPREM']
    for state, color in PREMIUM_COLORS.items():
        items = premiums[premiums.PR_STATE == state]
        axes[1].scatter(items.PR_DUEDT, items.PR_AMTDU, color=color, label=f'state {state}', s=15)
    axes[1].set_ylabel('Amount due')
    axes[1].set_title('Premium items (NRPREM)')
    axes[1].legend(loc='upper left')

    # Business events except the monthly charge run and premium receipt, which happen every month
    events = story['NREVNT'][~story['NREVNT'].EV_EVTTP.isin([110, 300])]
    axes[2].scatter(events.EV_EFFDT, events.EV_EVTTP, color='black', s=20)
    for row in events.itertuples():
        axes[2].annotate(row.EV_NAME, (row.EV_EFFDT, row.EV_EVTTP), fontsize=8, rotation=20)
    axes[2].set_ylabel('Event type')
    axes[2].set_title('Business events (NREVNT, without 110 and 300)')

    plt.tight_layout()
    output_filename = output_filename or f'timeline_{policy_id}.png'
    plt.savefig(get_path('Plots') / output_filename)
    plt.show()
