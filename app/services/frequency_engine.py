"""
Phase 2 — Frequency Engine
──────────────────────────
Answers the core analytics questions:
  - How often does each number appear? (frequency)
  - When did it last appear? (recency)
  - How long between appearances on average? (gap analysis)
  - Is it appearing more lately or less? (rolling frequency)
  - Composite weighted score combining all of the above

None of this predicts the future. What it does is describe
the past accurately — which is the honest foundation for
everything the ML and simulation engines build on top of.
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
from app.core.database import SessionLocal
from app.models.draw_model import Draw

# ── Constants ─────────────────────────────────────────────────

ALL_NUMBERS   = list(range(1, 50))     # 1 through 49
NUMBER_COLS   = ["n1", "n2", "n3", "n4", "n5", "n6"]

# Weights for the composite frequency score
# We care more about recent behaviour than all-time averages
WEIGHT_ALLTIME = 0.4
WEIGHT_RECENT  = 0.6

# "Recent" window in days
RECENT_DAYS = 90

# ── Data Loading ──────────────────────────────────────────────

def load_draws(draw_type: str = None) -> pd.DataFrame:
    """
    Pulls all draws from PostgreSQL into a pandas DataFrame.

    draw_type: "Lunchtime", "Teatime", or None (both combined)

    Why load into pandas?
    SQL is great for storage and retrieval. pandas is great for
    the kind of column-wise operations frequency analysis needs.
    We use each tool for what it's best at.
    """
    db   = SessionLocal()
    try:
        query = db.query(Draw)
        if draw_type:
            query = query.filter(Draw.draw_type == draw_type)
        rows = query.order_by(Draw.date.asc()).all()
    finally:
        db.close()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([{
        "date":      r.date,
        "draw_type": r.draw_type,
        "n1": r.n1, "n2": r.n2, "n3": r.n3,
        "n4": r.n4, "n5": r.n5, "n6": r.n6,
        "booster":   r.booster
    } for r in rows])

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Add a sequential draw index — useful for gap calculations
    # Draw 0 is the oldest, draw N is the most recent
    df["draw_index"] = df.index

    return df


def draws_to_number_series(df: pd.DataFrame) -> pd.Series:
    """
    Converts the wide format (n1, n2, n3, n4, n5, n6) into a
    long flat series of every number drawn.

    Wide format (one row per draw):
        date       n1  n2  n3  n4  n5  n6
        2020-01-01  5  12  23  34  41  47

    Long format (one row per number drawn):
        5, 12, 23, 34, 41, 47, ...

    The long format is what frequency counting needs.
    """
    return pd.Series(df[NUMBER_COLS].values.flatten())


# ── Core Analysis Functions ───────────────────────────────────

def compute_frequency(df: pd.DataFrame) -> pd.DataFrame:
    """
    Counts how many times each number (1–49) has appeared
    across all draws. Also computes:

    - count      : raw appearance count
    - expected   : what count would be if perfectly random
    - deviation  : how far above/below expected (in counts)
    - pct_diff   : percentage above or below expected

    A number with pct_diff of +10 appeared 10% more than chance.
    A number with pct_diff of -10 appeared 10% less than chance.
    """
    total_draws = len(df)
    # Each draw contributes 6 numbers to the pool
    expected_per_number = total_draws * (6 / 49)

    number_series = draws_to_number_series(df)
    counts = number_series.value_counts().reindex(
        ALL_NUMBERS, fill_value=0
    ).reset_index()
    counts.columns = ["number", "count"]

    counts["expected"]  = round(expected_per_number, 1)
    counts["deviation"] = counts["count"] - counts["expected"]
    counts["pct_diff"]  = round(
        (counts["deviation"] / counts["expected"]) * 100, 1
    )

    # Label hot / cold / neutral for easy reading
    counts["status"] = counts["pct_diff"].apply(
        lambda x: "🔥 Hot" if x > 5 else ("🧊 Cold" if x < -5 else "➖ Neutral")
    )

    return counts.sort_values("count", ascending=False).reset_index(drop=True)


def compute_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each number, calculates the gaps (in draw count) between
    each consecutive appearance.

    Example: number 7 appeared at draw indexes 10, 25, 60
             gaps = [15, 35]
             average gap = 25 draws

    This tells us: on average, how many draws pass between
    each appearance of this number?

    A number with a short average gap appears frequently.
    A number with a long average gap appears rarely.

    Also computes:
    - last_seen_index   : draw index of most recent appearance
    - draws_since       : how many draws have passed since
    - overdue_score     : draws_since / avg_gap
                          > 1.0 means it's "overdue" by its own history
    """
    total_draws    = len(df)
    latest_index   = total_draws - 1

    results = []

    for number in ALL_NUMBERS:
        # Find every draw index where this number appeared
        mask    = (df[NUMBER_COLS] == number).any(axis=1)
        indexes = df[mask]["draw_index"].tolist()

        if len(indexes) < 2:
            # Not enough appearances to calculate gaps
            results.append({
                "number":          number,
                "appearances":     len(indexes),
                "avg_gap":         None,
                "min_gap":         None,
                "max_gap":         None,
                "last_seen_index": indexes[-1] if indexes else None,
                "draws_since":     latest_index - indexes[-1] if indexes else None,
                "overdue_score":   None
            })
            continue

        gaps        = [indexes[i+1] - indexes[i] for i in range(len(indexes)-1)]
        avg_gap     = round(np.mean(gaps), 1)
        last_seen   = indexes[-1]
        draws_since = latest_index - last_seen

        results.append({
            "number":          number,
            "appearances":     len(indexes),
            "avg_gap":         avg_gap,
            "min_gap":         min(gaps),
            "max_gap":         max(gaps),
            "last_seen_index": last_seen,
            "draws_since":     draws_since,
            "overdue_score":   round(draws_since / avg_gap, 2) if avg_gap else None
        })

    return pd.DataFrame(results).sort_values(
        "overdue_score", ascending=False, na_position="last"
    ).reset_index(drop=True)


def compute_rolling(df: pd.DataFrame, days: int = RECENT_DAYS) -> pd.DataFrame:
    """
    Counts appearances of each number in the last N days only.

    This is different from all-time frequency — it captures
    whether a number is trending up or down recently.

    A number that appears 80 times overall but only 2 times
    in the last 90 days is losing momentum.

    A number that appears 60 times overall but 12 times in
    the last 90 days is gaining momentum.
    """
    cutoff = df["date"].max() - pd.Timedelta(days=days)
    recent = df[df["date"] >= cutoff]

    recent_counts = draws_to_number_series(recent).value_counts().reindex(
        ALL_NUMBERS, fill_value=0
    ).reset_index()
    recent_counts.columns = ["number", f"last_{days}d_count"]

    return recent_counts


def compute_frequency_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Combines all-time frequency and recent frequency into one
    weighted composite score per number.

    score = (all_time_freq_normalised × 0.4)
           + (recent_freq_normalised  × 0.6)

    Normalised means we scale each to 0–100 so they're
    comparable despite having different raw counts.

    This score is what the Prediction Engine will use as one
    of its inputs. A higher score = more historically active number.

    Remember: this does NOT predict the next draw.
    It describes past patterns — nothing more.
    """
    freq_df    = compute_frequency(df)
    rolling_df = compute_rolling(df)

    merged = freq_df.merge(rolling_df, on="number")

    # Normalise both to 0–100
    max_count  = merged["count"].max()
    max_recent = merged[f"last_{RECENT_DAYS}d_count"].max()

    merged["alltime_norm"] = (merged["count"] / max_count * 100).round(1)
    merged["recent_norm"]  = (
        merged[f"last_{RECENT_DAYS}d_count"] / max_recent * 100
        if max_recent > 0 else 0
    ).round(1)

    merged["frequency_score"] = (
        (merged["alltime_norm"] * WEIGHT_ALLTIME) +
        (merged["recent_norm"]  * WEIGHT_RECENT)
    ).round(2)

    # Reclassify status based on final score, not raw count
    # This ensures the label reflects the weighted score
    score_max = merged["frequency_score"].max()
    score_min = merged["frequency_score"].min()
    score_range = score_max - score_min

    merged["status"] = merged["frequency_score"].apply(
        lambda s: "🔥 Hot" if s >= score_max * 0.75
        else ("🧊 Cold" if s <= score_min + score_range * 0.25
        else "➖ Neutral")
    )

    return merged.sort_values(
        "frequency_score", ascending=False
    ).reset_index(drop=True)


# ── Full Report ───────────────────────────────────────────────

def get_full_report(draw_type: str = None) -> dict:
    """
    Master function that runs all analysis and returns a
    structured dictionary. This is what the FastAPI routes
    and Streamlit dashboard will call.

    draw_type: "Lunchtime", "Teatime", or None for combined
    """
    df = load_draws(draw_type)

    if df.empty:
        return {"error": "No data found"}

    label = draw_type or "All Draws"

    frequency  = compute_frequency(df)
    gaps       = compute_gaps(df)
    rolling    = compute_rolling(df)
    scores     = compute_frequency_score(df)

    # Top 10 hot numbers by frequency score
    hot_numbers  = scores.head(10)["number"].tolist()
    # Top 10 cold numbers (lowest score)
    cold_numbers = scores.tail(10)["number"].tolist()
    # Top 10 most overdue
    overdue      = gaps.dropna(subset=["overdue_score"]).head(10)

    return {
        "label":        label,
        "total_draws":  len(df),
        "date_range": {
            "from": str(df["date"].min().date()),
            "to":   str(df["date"].max().date())
        },
        "hot_numbers":  hot_numbers,
        "cold_numbers": cold_numbers,
        "overdue":      overdue[["number", "avg_gap", "draws_since", "overdue_score"]].to_dict("records"),
        "frequency":    frequency.to_dict("records"),
        "scores":       scores[["number", "frequency_score", "status"]].to_dict("records")
    }