"""
Phase 4a — Bayesian Engine
───────────────────────────
Updates probability estimates for each number using Bayes' theorem.

Why Bayesian?
Frequency analysis gives us raw counts. Bayesian analysis gives
us principled probability estimates that:
  - Start from a fair prior (uniform — no number favoured)
  - Update as evidence accumulates
  - Naturally handle uncertainty with small samples
  - Converge toward frequency analysis with large samples

With 2,200+ draws our posterior will be close to uniform —
consistent with what Phase 3 proved. The engine is honest.
"""

import numpy as np
import pandas as pd
from app.services.frequency_engine import (
    load_draws,
    compute_frequency,
    ALL_NUMBERS,
    NUMBER_COLS
)

# ── Constants ─────────────────────────────────────────────────

# Alpha (prior strength) — how strongly we believe in the
# uniform prior before seeing any data.
# Higher alpha = prior dominates even with lots of data
# Lower alpha  = data dominates quickly
# 49.0 means we weight the prior as if we had seen 49 draws
# where each number appeared exactly once — a weak, fair prior
PRIOR_ALPHA = 49.0

# ── Core Bayesian Update ──────────────────────────────────────

def compute_posterior(df: pd.DataFrame, alpha: float = PRIOR_ALPHA) -> pd.DataFrame:
    """
    Computes the Bayesian posterior probability for each number.

    Model: Beta-Binomial conjugate
    ─────────────────────────────
    For each number we model:
      - Prior: how likely we think it is before seeing data
      - Likelihood: how often it actually appeared
      - Posterior: our updated belief combining both

    Prior: uniform — each number equally likely (1/49)
    This encodes our belief that the lottery is fair.

    Posterior mean for number i:
      P(i) = (alpha_i + count_i) / (sum(all alphas) + total_observations)

    Where:
      alpha_i          = PRIOR_ALPHA / 49  (equal share of prior)
      count_i          = observed appearances of number i
      total_observations = total numbers drawn (draws × 6)
    """
    freq = compute_frequency(df)

    total_draws       = len(df)
    total_obs         = total_draws * 6   # Each draw produces 6 numbers
    prior_per_number  = alpha / len(ALL_NUMBERS)

    results = []
    for _, row in freq.iterrows():
        number  = row["number"]
        count   = row["count"]

        # Bayesian update
        posterior_alpha = prior_per_number + count
        posterior_sum   = alpha + total_obs

        posterior_prob  = posterior_alpha / posterior_sum

        # Compare to flat random probability
        random_prob     = 6 / 49   # Probability of appearing in one draw

        results.append({
            "number":          number,
            "count":           count,
            "prior_prob":      round(prior_per_number / (alpha), 6),
            "posterior_prob":  round(posterior_prob, 6),
            "random_prob":     round(random_prob / 49, 6),
            "lift":            round(posterior_prob / (alpha / (alpha + total_obs) / 49), 4)
        })

    result_df = pd.DataFrame(results)
    result_df["rank"] = result_df["posterior_prob"].rank(
        ascending=False
    ).astype(int)

    return result_df.sort_values("posterior_prob", ascending=False).reset_index(drop=True)


def compute_recent_posterior(
    df: pd.DataFrame,
    days: int   = 90,
    alpha: float = PRIOR_ALPHA
) -> pd.DataFrame:
    """
    Same as compute_posterior but weighted toward recent draws.

    Recent draws get full weight.
    Older draws get exponentially decayed weight — they matter
    less the further back they are.

    decay_weight = e^(-lambda × days_ago)
    where lambda controls how fast old data fades.
    """
    today      = df["date"].max()
    decay_rate = 0.01   # Tune this: higher = faster decay of old data

    # Weight each draw by recency
    df = df.copy()
    df["days_ago"] = (today - df["date"]).dt.days
    df["weight"]   = np.exp(-decay_rate * df["days_ago"])

    # Compute weighted counts for each number
    weighted_counts = {}
    for num in ALL_NUMBERS:
        mask = (df[NUMBER_COLS] == num).any(axis=1)
        weighted_counts[num] = df.loc[mask, "weight"].sum()

    total_weight     = sum(weighted_counts.values())
    prior_per_number = alpha / len(ALL_NUMBERS)

    results = []
    for number in ALL_NUMBERS:
        w_count         = weighted_counts[number]
        posterior_alpha = prior_per_number + w_count
        posterior_sum   = alpha + total_weight
        posterior_prob  = posterior_alpha / posterior_sum

        results.append({
            "number":               number,
            "weighted_count":       round(w_count, 2),
            "posterior_prob":       round(posterior_prob, 6),
            "recent_posterior":     round(posterior_prob, 6),
        })

    df_result = pd.DataFrame(results)
    df_result["rank"] = df_result["posterior_prob"].rank(
        ascending=False
    ).astype(int)

    return df_result.sort_values(
        "posterior_prob", ascending=False
    ).reset_index(drop=True)


def get_bayesian_report(draw_type: str = None) -> dict:
    """
    Full Bayesian report combining all-time and recent posteriors.
    Returns ranked numbers with probability estimates.
    """
    df    = load_draws(draw_type)
    label = draw_type or "All Draws"

    if df.empty:
        return {"error": "No data found"}

    alltime = compute_posterior(df)
    recent  = compute_recent_posterior(df)

    # Spread between highest and lowest posterior — how unequal are they?
    prob_spread = round(
        alltime["posterior_prob"].max() - alltime["posterior_prob"].min(), 8
    )

    return {
        "label":           label,
        "total_draws":     len(df),
        "prob_spread":     prob_spread,
        "top_10_alltime":  alltime.head(10)[["number", "posterior_prob", "rank"]].to_dict("records"),
        "top_10_recent":   recent.head(10)[["number", "recent_posterior", "rank"]].to_dict("records"),
        "all_posteriors":  alltime[["number", "posterior_prob"]].to_dict("records")
    }