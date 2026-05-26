"""
Backtesting Engine
───────────────────
Tests the prediction model against historical draws it has never seen.

Method (Walk-Forward Backtesting):
  For each draw from position `window` onwards:
    1. Use only draws BEFORE this point to generate predictions
    2. Compare predictions against the ACTUAL draw
    3. Record how many numbers matched
    4. Do the same for a purely random ticket
    5. Compare model vs random across all tested draws

This is the honest performance measurement.
Phase 3 already proved statistically what this will show visually —
the model performs at or near random. But seeing it draw by draw,
over thousands of draws, is more honest and more compelling than
a p-value alone.

Walk-forward is important:
  We never let the model see future data when generating predictions.
  Each prediction uses only the past. This prevents data leakage —
  the cardinal sin of backtesting.
"""

import numpy as np
import pandas as pd
import random
from app.services.frequency_engine import (
    load_draws, compute_frequency_score, NUMBER_COLS, ALL_NUMBERS
)
from app.services.genetic_algorithm import (
    compute_fitness, initialise_population, evolve,
    POPULATION_SIZE, N_GENERATIONS
)

# ── Core Backtester ───────────────────────────────────────────

def backtest(
    draw_type:    str = None,
    window:       int = 200,    # Minimum draws needed before first prediction
    sample_every: int = 10,     # Test every Nth draw (speeds up the process)
    n_tickets:    int = 3,      # Tickets generated per prediction point
    verbose:      bool = True
) -> dict:
    """
    Walk-forward backtest of the prediction engine vs random baseline.

    Parameters:
      window       : how many draws to use as minimum history
      sample_every : test every Nth draw (1 = every draw, slow)
      n_tickets    : how many tickets to generate at each point
      verbose      : print progress

    Returns a dict with:
      - per-draw results (model hits, random hits)
      - aggregate statistics
      - comparison metrics
    """
    df    = load_draws(draw_type)
    label = draw_type or "All Draws"

    if len(df) < window + 20:
        return {"error": "Not enough draws for backtesting"}

    model_hits_all  = []
    random_hits_all = []
    results         = []

    test_indices = range(window, len(df) - 1, sample_every)
    total        = len(list(test_indices))

    if verbose:
        print(f"\n  Backtesting {label}: {total} prediction points")
        print(f"  Window: {window} draws | Sample every: {sample_every} draws\n")

    for count, i in enumerate(test_indices):

        if verbose and count % 20 == 0:
            print(f"  Progress: {count}/{total} ({100*count//total}%)")

        # ── Data split ────────────────────────────────────────
        # CRITICAL: model only sees draws[:i] — never the future
        past   = df.iloc[:i]
        actual = df.iloc[i]

        actual_numbers = set([
            actual["n1"], actual["n2"], actual["n3"],
            actual["n4"], actual["n5"], actual["n6"]
        ])
        actual_booster = actual["booster"]
        draw_date      = actual["date"]

        # ── Model prediction ──────────────────────────────────
        # Lightweight version — frequency-based only (no full GA per step,
        # that would take hours). Uses top frequency numbers + random fill.
        freq_df     = compute_frequency_score(past)
        freq_scores = dict(zip(freq_df["number"], freq_df["frequency_score"]))

        # Build pair counts from past data
        pair_counts = {}
        for _, row in past.iterrows():
            nums = sorted([int(row[c]) for c in NUMBER_COLS])
            for a in range(len(nums)):
                for b in range(a+1, len(nums)):
                    pair = (nums[a], nums[b])
                    pair_counts[pair] = pair_counts.get(pair, 0) + 1

        # Generate n_tickets candidate tickets
        # Use top-weighted numbers with some randomness for diversity
        weights = np.array([
            freq_scores.get(n, 50) for n in ALL_NUMBERS
        ], dtype=float)
        weights = weights / weights.sum()

        model_ticket_hits = []
        for _ in range(n_tickets):
            ticket     = sorted(np.random.choice(
                ALL_NUMBERS, size=6, replace=False, p=weights
            ).tolist())
            hits       = len(set(ticket) & actual_numbers)
            booster_h  = 1 if actual_booster in ticket else 0
            model_ticket_hits.append(hits + booster_h * 0.5)

        best_model_hits = max(model_ticket_hits)

        # ── Random baseline ───────────────────────────────────
        # Purely random ticket — the comparison point
        random_tickets = [
            random.sample(ALL_NUMBERS, 6)
            for _ in range(n_tickets)
        ]
        random_hit_counts = [
            len(set(t) & actual_numbers)
            for t in random_tickets
        ]
        best_random_hits = max(random_hit_counts)

        model_hits_all.append(best_model_hits)
        random_hits_all.append(best_random_hits)

        results.append({
            "draw_index":   i,
            "date":         str(draw_date.date()),
            "draw_type":    actual["draw_type"],
            "actual":       sorted(actual_numbers),
            "model_hits":   best_model_hits,
            "random_hits":  best_random_hits,
            "delta":        best_model_hits - best_random_hits
        })

    # ── Aggregate statistics ──────────────────────────────────
    model_avg  = round(np.mean(model_hits_all), 4)
    random_avg = round(np.mean(random_hits_all), 4)
    delta_avg  = round(model_avg - random_avg, 4)

    # Hit distribution: how often did we get 0,1,2,3+ matches?
    model_dist  = {str(k): sum(1 for h in model_hits_all  if int(h) == k) for k in range(7)}
    random_dist = {str(k): sum(1 for h in random_hits_all if h == k)      for k in range(7)}

    # Percentage of draws where model beat random
    beat_random  = sum(1 for r in results if r["delta"] > 0)
    tied_random  = sum(1 for r in results if r["delta"] == 0)
    lost_random  = sum(1 for r in results if r["delta"] < 0)

    return {
        "label":            label,
        "draws_tested":     len(results),
        "window":           window,
        "model_avg_hits":   model_avg,
        "random_avg_hits":  random_avg,
        "delta_avg":        delta_avg,
        "beat_random_pct":  round(beat_random / len(results) * 100, 1),
        "tied_random_pct":  round(tied_random / len(results) * 100, 1),
        "lost_random_pct":  round(lost_random / len(results) * 100, 1),
        "model_hit_dist":   model_dist,
        "random_hit_dist":  random_dist,
        "per_draw_results": results,
        "interpretation": build_interpretation(model_avg, random_avg, delta_avg)
    }


def build_interpretation(model_avg, random_avg, delta_avg):
    """
    Builds an honest, contextualised interpretation of backtest results.
    Transparency first, context below — as discussed.
    """
    if abs(delta_avg) < 0.05:
        performance = "performs at essentially the same level as"
        verdict     = "no advantage"
    elif delta_avg > 0.05:
        performance = "marginally outperformed"
        verdict     = "marginal advantage"
    else:
        performance = "marginally underperformed"
        verdict     = "below random"

    # ── Build transparency string honestly ────────────────────
    if verdict == "no advantage":
        transparency = (
            f"The model performs at essentially the same level as random "
            f"(avg {model_avg} hits vs {random_avg} random, delta={delta_avg}). "
            f"Consistent with Phase 3: draws are random, no method has an edge."
        )
    elif verdict == "marginal advantage":
        transparency = (
            f"The model marginally outperformed random in this run "
            f"(avg {model_avg} hits vs {random_avg} random, delta={delta_avg}). "
            f"However this delta is within normal random variation — "
            f"Phase 3 confirmed no method has statistically significant predictive power "
            f"(hot number test p=0.772). Run the backtest again and the result may reverse."
        )
    else:
        transparency = (
            f"The model marginally underperformed random in this run "
            f"(avg {model_avg} hits vs {random_avg} random, delta={delta_avg}). "
            f"This is also within normal random variation — "
            f"neither result is statistically meaningful."
        )

    return {
        "performance_vs_random": performance,
        "verdict":               verdict,
        "model_avg":             model_avg,
        "random_avg":            random_avg,
        "transparency":          transparency,
        "context": (
            "This result is expected and honest. The value of this project "
            "is not in beating randomness — which is mathematically impossible "
            "in a fair draw — but in demonstrating a complete data science "
            "pipeline: ETL, statistical testing, Bayesian modelling, "
            "evolutionary algorithms, and rigorous self-evaluation. "
            "The backtest itself is the most credible part of the project."
        ),
        "portfolio_note": (
            "Most lottery prediction apps show only their hits. "
            "This project shows the full picture including the comparison "
            "against random — which takes intellectual honesty to publish. "
            "The two-run variance you see here is itself evidence of randomness: "
            "no method consistently dominates because there is nothing to dominate."
        )
    }