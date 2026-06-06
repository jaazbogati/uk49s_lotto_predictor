"""
Pattern Engine — Pair and Triple Analysis
──────────────────────────────────────────
Tracks which numbers appear together most frequently.

A pair is any two numbers that appeared in the same draw.
With 6 numbers per draw, each draw produces C(6,2) = 15 pairs.

This engine:
  - Counts all pair co-occurrences across history
  - Weights recent pairs more heavily
  - Scores pairs by frequency + recency
  - Returns top N pairs as predictions
  - Supports hit checking against actual draws

Phase 3 reminder: pair frequency has no predictive power
over future draws. This is pattern description, not prediction.
"""

import pandas as pd
import numpy as np
from itertools import combinations
from app.services.frequency_engine import load_draws, NUMBER_COLS


# ── Core Pair Counter ─────────────────────────────────────────

def compute_pairs(df: pd.DataFrame, days_recent: int = 90) -> pd.DataFrame:
    """
    Counts every pair co-occurrence across all draws.

    For each draw, generates all C(6,2) = 15 number pairs
    and increments their count.

    Also computes a recency-weighted count using exponential
    decay — pairs that appeared recently score higher.

    Returns a DataFrame with columns:
      n1, n2, count, recent_count, score, last_seen_date
    """
    today      = df["date"].max()
    decay_rate = 0.02
    cutoff     = today - pd.Timedelta(days=days_recent)

    pair_counts        = {}
    pair_recent        = {}
    pair_last_seen     = {}

    for _, row in df.iterrows():
        nums    = sorted([int(row[c]) for c in NUMBER_COLS])
        date    = row["date"]
        days_ago = (today - date).days
        weight  = np.exp(-decay_rate * days_ago)

        for n1, n2 in combinations(nums, 2):
            key = (n1, n2)

            pair_counts[key]    = pair_counts.get(key, 0) + 1
            pair_recent[key]    = pair_recent.get(key, 0) + weight

            if key not in pair_last_seen or date > pair_last_seen[key]:
                pair_last_seen[key] = date

    # Build DataFrame
    records = []
    for (n1, n2), count in pair_counts.items():
        records.append({
            "n1":           n1,
            "n2":           n2,
            "pair":         f"{n1}-{n2}",
            "count":        count,
            "recent_score": round(pair_recent.get((n1, n2), 0), 4),
            "last_seen":    str(pair_last_seen.get((n1, n2), "").date()
                               if hasattr(pair_last_seen.get((n1, n2)), 'date')
                               else pair_last_seen.get((n1, n2), "")),
        })

    df_pairs = pd.DataFrame(records)

    # Normalise both counts to 0-100
    max_count  = df_pairs["count"].max()
    max_recent = df_pairs["recent_score"].max()

    df_pairs["count_norm"]  = (df_pairs["count"]        / max_count  * 100).round(2)
    df_pairs["recent_norm"] = (df_pairs["recent_score"] / max_recent * 100).round(2)

    # Weighted composite score — recency weighted more
    df_pairs["score"] = (
        df_pairs["count_norm"]  * 0.4 +
        df_pairs["recent_norm"] * 0.6
    ).round(4)

    return df_pairs.sort_values("score", ascending=False).reset_index(drop=True)


def get_top_pairs(draw_type: str = None, n: int = 20) -> list:
    """
    Returns the top N pairs as a list of dicts.
    Used by the predictor and API.
    """
    df    = load_draws(draw_type)
    pairs = compute_pairs(df)

    return pairs.head(n)[[
        "pair", "n1", "n2", "count", "score", "last_seen"
    ]].to_dict("records")


def check_pair_hits(pairs: list, actual_numbers: list) -> dict:
    """
    Checks how many of the predicted pairs appeared in an actual draw.

    A pair "hits" if BOTH numbers appeared in the draw.

    pairs:          list of dicts with 'n1', 'n2', 'pair' keys
    actual_numbers: list of 6 numbers from the actual draw

    Returns:
      hit_count:    how many pairs hit
      hit_pairs:    which specific pairs hit
      hit_rate:     percentage of predicted pairs that hit
      near_misses:  pairs where one number appeared but not both
    """
    actual_set  = set(actual_numbers)
    hit_pairs   = []
    near_misses = []

    for p in pairs:
        n1, n2 = p["n1"], p["n2"]
        if n1 in actual_set and n2 in actual_set:
            hit_pairs.append(p["pair"])
        elif n1 in actual_set or n2 in actual_set:
            near_misses.append(p["pair"])

    return {
        "predicted_pairs": len(pairs),
        "hit_count":       len(hit_pairs),
        "hit_pairs":       hit_pairs,
        "hit_rate":        round(len(hit_pairs) / len(pairs) * 100, 1) if pairs else 0,
        "near_miss_count": len(near_misses),
        "near_misses":     near_misses,
        "random_baseline": round(
            # Expected pairs from random: C(6,2)/C(49,2) * n_predicted
            (15 / 1176) * len(pairs), 4
        )
    }