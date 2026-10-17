"""Rule finder: show where a calculated value differs from the target, as readable conditions.

Works for any task: give it one row per value with the columns that might matter (dates, codes, amounts) and a flag
that says if the current rule got the value wrong. A shallow decision tree learns which conditions separate the
wrong rows from the right ones, and its splits are the hidden rules, e.g. "APPDT <= 2007.6" for a system change.
"""
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text


def year_fraction(dates):
    """Convert dates into decimal years (2007-08-11 -> 2007.61), so tree thresholds can be read as dates.
    Parameters: dates (pd.Series): Timestamps.
    Returns (pd.Series): Decimal years.
    """
    return dates.dt.year + (dates.dt.dayofyear - 1) / 365.25


def prepare_features(features):
    """Turn a table of mixed columns into numbers a decision tree can split.
    Dates become decimal years, text columns one 0/1 column per value, numbers stay as they are.
    Parameters: features (pd.DataFrame): Candidate explanations, one row per value.
    Returns (pd.DataFrame): Numeric features.
    """
    numeric = features.copy()
    for column in numeric.columns:
        if pd.api.types.is_datetime64_any_dtype(numeric[column]):
            numeric[column] = year_fraction(numeric[column])
    numeric = pd.get_dummies(numeric, dtype=float)
    return numeric.astype(float).fillna(-1)


def find_rules(features, wrong, max_depth=3, min_samples_leaf=5):
    """Fit a shallow decision tree that predicts where the current rule is wrong, and print its conditions.
    Parameters: features (pd.DataFrame): Candidate explanations, one row per value; wrong (pd.Series): True where the
        calculated value differs from the target; max_depth (int): Depth of the tree, small so that the rules stay
        readable; min_samples_leaf (int): Smallest group a rule may describe, larger values ignore single outliers.
    Returns (str): The tree as indented if/else conditions.
    """
    numeric = prepare_features(features)
    tree = DecisionTreeClassifier(max_depth=max_depth, min_samples_leaf=min_samples_leaf, class_weight='balanced',
                                  random_state=42)
    tree.fit(numeric, wrong)

    rules = export_text(tree, feature_names=list(numeric.columns), class_names=['right', 'wrong'], decimals=2)
    print(f'{wrong.sum()} of {len(wrong)} values wrong ({wrong.mean():.2%})')
    print(rules)
    return rules


def plot_wrong_over_time(dates, wrong, title, freq='YE'):
    """Plot the share of wrong values over time: a sudden jump points to a system or parameter change.
    Parameters: dates (pd.Series): Date of each value, e.g. the application date; wrong (pd.Series): True where the
        calculated value differs from the target; title (str): Title of the plot; freq (str): Size of the time buckets,
        default one year.
    """
    share = wrong.groupby(dates.dt.to_period(freq[0])).mean()
    plt.figure(figsize=(12, 3))
    share.plot(marker='o', color='black')
    plt.title(title)
    plt.ylabel('Share wrong')
    plt.grid()
    plt.show()
