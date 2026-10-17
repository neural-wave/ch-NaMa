"""Policy timeline viewer: everything Neuron knows about one policy, in one place.

    python tools/policy_timeline.py BL10000013

prints the policy story and saves a timeline plot to Plots/timeline_<policy>.png.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from legacy_loader import LegacyData  # noqa: E402
from tools.policy_story import POLICY_TABLES, policy_story, print_story  # noqa: E402
from tools.plot_paths import PROJECT_FOLDER, CACHE_DIR, get_path  # noqa: E402
from tools.timeline_plot import PREMIUM_COLORS, plot_timeline  # noqa: E402


# Policy tables and the column that holds their policy number


if __name__ == '__main__':
    policy = sys.argv[1] if len(sys.argv) > 1 else 'BL10000013'
    legacy = LegacyData(cache_dir=CACHE_DIR)
    policy_data = policy_story(legacy, policy)
    print_story(policy_data)
    plot_timeline(policy_data)
