"""Policy timeline viewer: everything Neuron knows about one policy, in one place.

    python tools/policy_timeline.py BL10000013

prints the policy story and saves a timeline plot to Plots/timeline_<policy>.png.
"""
import os
import pathlib
import sys

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from legacy_loader import LegacyData  # noqa: E402

PROJECT_FOLDER = pathlib.Path(__file__).resolve().parents[3]
CACHE_DIR = PROJECT_FOLDER / '.cache'

# Policy tables and the column that holds their policy number
POLICY_TABLES = {
    'NRPOLH': 'PH_POLNR', 'NRRISK': 'RK_POLNR', 'NRHOLD': 'HD_POLNR', 'NRALLO': 'AL_POLNR',
    'NRAGRE': 'AG_POLNR', 'NRPREM': 'PR_POLNR', 'NREVNT': 'EV_POLNR', 'NRBOOK': 'BK_POLNR',
    'NRTAXB': 'TB_POLNR', 'NREXCP': 'EX_POLNR',
}

PREMIUM_COLORS = {'P': 'tab:green', 'R': 'tab:red', 'O': 'tab:orange', 'W': 'tab:gray'}


def get_path(folder_name):
    """
    Get the absolute path of a folder in the project folder, and create it if needed.

    Parameters:
    - folder_name (str): Name of the folder.

    Returns:
    - pathlib.Path: Absolute path of the folder.
    """
    folder_path = PROJECT_FOLDER / folder_name
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


def policy_story(data, policy_id):
    """
    Collect the rows of every table that belong to one policy, plus its person, broker and product.

    Parameters:
    - data (LegacyData): Loaded legacy export.
    - policy_id (str): Policy number without blanks, e.g. 'BL10000013'.

    Returns:
    - dict: {table name: pd.DataFrame} with the rows of this policy.
    """
    story = {}
    for name, column in POLICY_TABLES.items():
        table = data.table(name)
        story[name] = table[table[column] == policy_id].reset_index(drop=True)

    # Linked master data: insured person, policyholder, broker and product
    persons = set(story['NRRISK'].RK_PERNR) | set(story['NRHOLD'].HD_PERNR)
    story['NRPERS'] = data.table('NRPERS').query('PS_PERNR in @persons').reset_index(drop=True)
    brokers = set(story['NRPOLH'].PH_BRKNR)
    story['NRBROK'] = data.table('NRBROK').query('BR_BRKNR in @brokers').reset_index(drop=True)
    products = set(story['NRPOLH'].PH_PRDCD)
    story['NRPROD'] = data.table('NRPROD').query('PD_PRDCD in @products').reset_index(drop=True)

    # Readable texts for the event and booking codes
    event_names = data.codes('EVTTP')
    story['NREVNT']['EV_NAME'] = story['NREVNT'].EV_EVTTP.astype(str).map(event_names)
    return story


def print_story(story, max_rows=15):
    """
    Print a short overview of every table of a policy story.

    Parameters:
    - story (dict): Result of `policy_story`.
    - max_rows (int): Maximum number of rows printed per table.

    Returns:
    - None
    """
    for name, table in story.items():
        print(f'\n{name}: {len(table)} rows', 20 * '#')
        if len(table):
            print(table.head(max_rows).to_string())


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


if __name__ == '__main__':
    policy = sys.argv[1] if len(sys.argv) > 1 else 'BL10000013'
    legacy = LegacyData(cache_dir=CACHE_DIR)
    policy_data = policy_story(legacy, policy)
    print_story(policy_data)
    plot_timeline(policy_data)
