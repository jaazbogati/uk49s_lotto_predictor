"""
Phase 3 — Statistical Engine
─────────────────────────────
Proves or disproves the core assumptions lottery players make.

This is where the project stops being a pattern finder and
becomes a scientific instrument. Every function here produces
a concrete, defensible statistical result.

Key concepts used:
  - Chi-square test    : are observed frequencies what randomness predicts?
  - P-value            : probability the result occurred by chance
  - Pearson r          : correlation between two variables (-1 to +1)
  - Effect size        : how big is the difference, not just is it real
"""

import pandas as pd
import numpy as np
from scipy import stats
from app.services.frequency_engine import (
    load_draws,
    compute_frequency,
    compute_gaps,
    compute_frequency_score,
    NUMBER_COLS,
    ALL_NUMBERS
)

# ── Test 1 — Chi-Square Goodness of Fit ──────────────────────

def test_randomness(draw_type: str = None) -> dict:
    """
    Tests whether the distribution of number frequencies is
    consistent with a truly random draw.

    How it works:
    - We count how many times each number actually appeared (observed)
    - We calculate how many times it SHOULD appear if random (expected)
    - Chi-square measures the total deviation between observed and expected
    - The p-value tells us if that deviation could happen by chance

    Expected count per number = total_draws × (6/49)
    """
    df    = load_draws(draw_type)
    label = draw_type or "All Draws"

    freq  = compute_frequency(df)
    observed  = freq["count"].values.astype(float)

    # Recompute expected directly from observed sum so totals match exactly.
    # We can't use the pre-rounded "expected" column because scipy requires
    # sum(observed) == sum(expected) to floating point precision.
    # The ratio 6/49 is constant — we just scale it to match observed total.
    total_observed = observed.sum()
    expected = np.full(len(ALL_NUMBERS), total_observed / len(ALL_NUMBERS))

    chi2, p_value = stats.chisquare(observed, f_exp=expected)

    # Degrees of freedom = number of categories - 1
    dof = len(ALL_NUMBERS) - 1

    # Effect size — Cramér's V normalises chi2 so we can compare
    # across different dataset sizes. Small: <0.1, Medium: 0.3, Large: >0.5
    n         = observed.sum()
    cramers_v = round(np.sqrt(chi2 / (n * (1))), 4)

    is_random = p_value > 0.05

    return {
        "test":        "Chi-Square Goodness of Fit",
        "draw_type":   label,
        "total_draws": len(df),
        "chi2":        round(chi2, 4),
        "p_value":     round(p_value, 6),
        "dof":         dof,
        "cramers_v":   cramers_v,
        "is_random":   is_random,
        "conclusion": (
            f"✅ Cannot reject randomness (p={round(p_value,4)}) — "
            f"distribution is consistent with a fair draw."
            if is_random else
            f"⚠️  Randomness rejected (p={round(p_value,4)}) — "
            f"distribution is unlikely to be purely random."
        )
    }

# ── Test 2 — Forward Frequency Test ──────────────────────────

def test_hot_number_predictive_power(
    draw_type: str = None,
    window: int    = 100,
    top_n: int     = 10
) -> dict:
    """
    The direct test of the Gambler's logic:
    "Hot numbers are more likely to appear next."

    Method:
    For each draw from position `window` onwards:
      1. Calculate the top_n hot numbers using only the previous
         `window` draws (no peeking at future data)
      2. Check how many of those hot numbers appeared in the
         actual next draw
      3. Compare the hit rate against what random chance predicts

    Random expectation:
      Probability of any given number appearing in one draw = 6/49
      Expected hits from top_n numbers = top_n × (6/49)

    If hot numbers have predictive power:
      actual_hit_rate > random_hit_rate (consistently)

    If they don't:
      actual_hit_rate ≈ random_hit_rate
    """
    df    = load_draws(draw_type)
    label = draw_type or "All Draws"

    if len(df) < window + 10:
        return {"error": "Not enough draws for this test"}

    random_expected_hits = top_n * (6 / 49)
    hit_counts           = []

    for i in range(window, len(df) - 1):
        # Historical window — only data before draw i
        past_draws = df.iloc[:i]

        # Compute frequency on past data only
        past_freq  = compute_frequency(past_draws)
        hot_nums   = set(past_freq.head(top_n)["number"].tolist())

        # Actual next draw
        next_draw  = df.iloc[i + 1]
        actual     = set(next_draw[NUMBER_COLS].values)

        # How many hot numbers appeared?
        hits = len(hot_nums & actual)
        hit_counts.append(hits)

    actual_hit_rate = round(np.mean(hit_counts), 4)
    std_dev         = round(np.std(hit_counts), 4)

    # One-sample t-test: is the actual hit rate significantly
    # different from the random expected hit rate?
    t_stat, p_value = stats.ttest_1samp(hit_counts, random_expected_hits)

    better_than_random = (
        actual_hit_rate > random_expected_hits and p_value < 0.05
    )

    return {
        "test":                 "Hot Number Predictive Power",
        "draw_type":            label,
        "draws_tested":         len(hit_counts),
        "window":               window,
        "top_n_hot":            top_n,
        "random_expected_hits": round(random_expected_hits, 4),
        "actual_avg_hits":      actual_hit_rate,
        "std_dev":              std_dev,
        "t_statistic":          round(t_stat, 4),
        "p_value":              round(p_value, 6),
        "better_than_random":   better_than_random,
        "conclusion": (
            f"✅ Hot numbers show predictive power "
            f"(avg {actual_hit_rate} hits vs {round(random_expected_hits,4)} random, p={round(p_value,4)})"
            if better_than_random else
            f"❌ Hot numbers show NO predictive power "
            f"(avg {actual_hit_rate} hits vs {round(random_expected_hits,4)} random, p={round(p_value,4)})"
        )
    }

# ── Test 3 — Overdue Score Predictive Test ───────────────────

def test_overdue_predictive_power(
    draw_type: str = None,
    window: int    = 100
) -> dict:
    """
    Tests whether the overdue score predicts next appearance.

    For each draw from `window` onwards:
      1. Compute overdue scores using past data only
      2. Record which numbers actually appeared
      3. Record their overdue scores at that moment

    Then: is there a correlation between overdue score and
    probability of appearing in the next draw?

    Pearson r ranges from -1 to +1:
      +1 = perfect positive correlation (overdue → more likely)
       0 = no correlation (overdue score is useless)
      -1 = perfect negative correlation (overdue → less likely)

    We also run a point-biserial correlation:
      appeared (1) vs didn't appear (0) against overdue score
    """
    df    = load_draws(draw_type)
    label = draw_type or "All Draws"

    if len(df) < window + 10:
        return {"error": "Not enough draws for this test"}

    overdue_scores_appeared   = []  # Overdue scores of numbers that DID appear
    overdue_scores_didnt      = []  # Overdue scores of numbers that did NOT appear

    for i in range(window, len(df) - 1):
        past_draws  = df.iloc[:i]
        gaps_df     = compute_gaps(past_draws)
        next_draw   = df.iloc[i + 1]
        appeared    = set(next_draw[NUMBER_COLS].values)

        for _, row in gaps_df.iterrows():
            if pd.isna(row["overdue_score"]):
                continue
            if row["number"] in appeared:
                overdue_scores_appeared.append(row["overdue_score"])
            else:
                overdue_scores_didnt.append(row["overdue_score"])

    avg_overdue_appeared  = round(np.mean(overdue_scores_appeared), 4)
    avg_overdue_didnt     = round(np.mean(overdue_scores_didnt), 4)

    # Mann-Whitney U test — does one group have higher overdue scores?
    # We use this instead of t-test because overdue scores aren't
    # normally distributed
    u_stat, p_value = stats.mannwhitneyu(
        overdue_scores_appeared,
        overdue_scores_didnt,
        alternative="two-sided"
    )

    overdue_predicts = (
        avg_overdue_appeared > avg_overdue_didnt and p_value < 0.05
    )

    return {
        "test":                      "Overdue Score Predictive Power",
        "draw_type":                 label,
        "avg_overdue_when_appeared": avg_overdue_appeared,
        "avg_overdue_when_didnt":    avg_overdue_didnt,
        "u_statistic":               round(u_stat, 2),
        "p_value":                   round(p_value, 6),
        "overdue_predicts":          overdue_predicts,
        "conclusion": (
            f"✅ Overdue scores DO predict appearance "
            f"(appeared avg: {avg_overdue_appeared} vs didn't: {avg_overdue_didnt}, p={round(p_value,4)})"
            if overdue_predicts else
            f"❌ Overdue scores do NOT predict appearance "
            f"(appeared avg: {avg_overdue_appeared} vs didn't: {avg_overdue_didnt}, p={round(p_value,4)})"
        )
    }

# ── Test 4 — Lunchtime vs Teatime Independence ────────────────

def test_draw_independence() -> dict:
    """
    Tests whether Lunchtime and Teatime draws are independent.

    If draws are truly independent random events, knowing what
    appeared in the Lunchtime draw should tell you NOTHING about
    what will appear in the Teatime draw.

    Method:
    - For each day, check if the same number appeared in both draws
    - Calculate the observed co-occurrence rate
    - Compare against the expected co-occurrence rate if independent

    Expected co-occurrence probability for any number on any day:
    P(appears in Lunch) × P(appears in Tea) = (6/49) × (6/49) ≈ 0.015
    """
    lunch = load_draws("Lunchtime").set_index("date")
    tea   = load_draws("Teatime").set_index("date")

    # Find days where both draws happened
    common_dates = lunch.index.intersection(tea.index)

    observed_cooccurrences = []
    expected_rate          = (6/49) ** 2

    for date in common_dates:
        lunch_nums = set(lunch.loc[date, NUMBER_COLS].values)
        tea_nums   = set(tea.loc[date, NUMBER_COLS].values)
        shared     = len(lunch_nums & tea_nums)
        observed_cooccurrences.append(shared)

    avg_shared      = round(np.mean(observed_cooccurrences), 4)
    expected_shared = round(expected_rate * 49, 4)

    t_stat, p_value = stats.ttest_1samp(
        observed_cooccurrences, expected_shared
    )

    are_independent = p_value > 0.05

    return {
        "test":                "Lunchtime vs Teatime Independence",
        "days_compared":       len(common_dates),
        "avg_shared_numbers":  avg_shared,
        "expected_if_random":  expected_shared,
        "t_statistic":         round(t_stat, 4),
        "p_value":             round(p_value, 6),
        "are_independent":     are_independent,
        "conclusion": (
            f"✅ Draws appear independent "
            f"(avg {avg_shared} shared vs {expected_shared} expected, p={round(p_value,4)})"
            if are_independent else
            f"⚠️  Draws may NOT be independent "
            f"(avg {avg_shared} shared vs {expected_shared} expected, p={round(p_value,4)})"
        )
    }

# ── Full Report ───────────────────────────────────────────────

def get_stats_report(draw_type: str = None) -> dict:
    """
    Runs all four tests and returns a combined report.
    This is what the FastAPI endpoint and dashboard will call.
    Note: test_hot_number_predictive_power is slow on large
    datasets because it loops through every draw. Be patient.
    """
    print(f"  Running chi-square test...")
    randomness = test_randomness(draw_type)

    print(f"  Running hot number test (this takes ~30 seconds)...")
    hot_power  = test_hot_number_predictive_power(draw_type)

    print(f"  Running overdue test (this takes ~60 seconds)...")
    overdue    = test_overdue_predictive_power(draw_type)

    print(f"  Running independence test...")
    indep      = test_draw_independence()

    return {
        "randomness_test":    randomness,
        "hot_number_test":    hot_power,
        "overdue_test":       overdue,
        "independence_test":  indep
    }