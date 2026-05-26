"""
Phase 6 — Prediction Engine
─────────────────────────────
Combines all engines into one honest, transparent output.

Pipeline:
  Phase 2 (Frequency) → hot numbers + overdue scores
  Phase 4a (Bayesian) → posterior probabilities
  Phase 4b (Monte Carlo) → candidate ticket pool
  Phase 5 (Genetic Algorithm) → evolved high-fitness tickets
  Phase 6 (This file) → combine, score, rank, explain

Honesty contract:
  Every output carries the statistical context from Phase 3.
  We show the analysis AND the proof that it doesn't beat random.
  Users make informed decisions, not false ones.
"""

import pandas as pd
import numpy as np
from app.services.frequency_engine import (
    load_draws,
    compute_frequency_score,
    compute_gaps,
    get_full_report as freq_report
)
from app.services.bayesian_engine  import get_bayesian_report
from app.services.monte_carlo      import get_monte_carlo_report
from app.services.genetic_algorithm import evolve

# ── Scoring Weights ───────────────────────────────────────────
# How much each engine contributes to the final ticket score.
# These are transparent and adjustable.

W_FREQUENCY = 0.35   # Historical frequency (Phase 2)
W_BAYESIAN  = 0.35   # Bayesian posterior   (Phase 4a)
W_GA        = 0.30   # GA fitness score     (Phase 5)

# ── Number-Level Scoring ──────────────────────────────────────

def score_numbers(draw_type: str = None) -> pd.DataFrame:
    """
    Produces a unified score per number combining
    frequency engine and Bayesian engine outputs.

    This is the number-level view:
    "How does each individual number rank across all engines?"
    """
    df         = load_draws(draw_type)
    freq_df    = compute_frequency_score(df)
    bayes      = get_bayesian_report(draw_type)
    bayes_df   = pd.DataFrame(bayes["all_posteriors"])

    merged = freq_df[["number", "frequency_score", "status"]].merge(
        bayes_df, on="number"
    )

    # Normalise Bayesian posterior to 0–100 to match frequency scale
    max_post = merged["posterior_prob"].max()
    min_post = merged["posterior_prob"].min()
    rng      = max_post - min_post if max_post != min_post else 1

    merged["bayes_norm"] = (
        (merged["posterior_prob"] - min_post) / rng * 100
    ).round(2)

    # Combined number score
    merged["combined_score"] = (
        merged["frequency_score"] * W_FREQUENCY +
        merged["bayes_norm"]      * W_BAYESIAN
    ).round(4)

    # Add gap/overdue data
    gaps_df = compute_gaps(df)[["number", "avg_gap", "draws_since", "overdue_score"]]
    merged  = merged.merge(gaps_df, on="number", how="left")

    return merged.sort_values(
        "combined_score", ascending=False
    ).reset_index(drop=True)


# ── Ticket-Level Scoring ──────────────────────────────────────

def score_ticket(ticket: list, number_scores: pd.DataFrame) -> dict:
    """
    Scores a complete 6-number ticket using the number-level scores.

    Metrics:
    - avg_combined_score : mean combined score of the 6 numbers
    - min_score          : weakest number in the ticket
    - coverage           : how spread across 1–49 the numbers are
    - odd_even_balance   : deviation from ideal 3/3 split
    - high_low_balance   : deviation from ideal 3/3 split
    """
    scores = []
    for n in ticket:
        row = number_scores[number_scores["number"] == n]
        if not row.empty:
            scores.append(row.iloc[0]["combined_score"])

    avg_score   = round(np.mean(scores), 4) if scores else 0
    min_score   = round(min(scores), 4) if scores else 0

    # Structural balance
    sorted_t    = sorted(ticket)
    spread      = (sorted_t[-1] - sorted_t[0]) / 48   # 0–1
    odds        = sum(1 for n in ticket if n % 2 != 0)
    highs       = sum(1 for n in ticket if n > 24)
    odd_balance = 1 - abs(odds - 3) / 3
    hl_balance  = 1 - abs(highs - 3) / 3

    overall = round(
        float(avg_score) * 0.5 +
        float(spread)    * 25  +
        float(odd_balance) * 12.5 +
        float(hl_balance)  * 12.5,
        4
    )

    return {
        "ticket":          sorted(ticket),
        "avg_num_score":   float(avg_score),
        "min_num_score":   float(min_score),
        "spread":          float(round(spread, 4)),
        "odd_even":        f"{odds} odd / {6-odds} even",
        "high_low":        f"{highs} high / {6-highs} low",
        "overall_score":   float(overall)
    }


# ── Main Prediction Function ──────────────────────────────────

def generate_predictions(
    draw_type:   str  = None,
    n_tickets:   int  = 5,
    verbose:     bool = True
) -> dict:
    """
    Full prediction pipeline. Runs all engines and returns
    ranked ticket suggestions with complete transparency.

    Steps:
    1. Score all 49 numbers (frequency + Bayesian)
    2. Run Monte Carlo for candidate pool
    3. Run GA evolution (seeded from Monte Carlo)
    4. Score all candidates
    5. Return top n_tickets with breakdown
    """
    label = draw_type or "All Draws"

    if verbose:
        print(f"\n  [1/4] Scoring numbers ({label})...")
    num_scores = score_numbers(draw_type)

    if verbose:
        print(f"  [2/4] Running Monte Carlo...")
    mc      = get_monte_carlo_report(draw_type, n_sims=50_000)
    mc_tickets = mc["candidate_tickets"]

    if verbose:
        print(f"  [3/4] Running Genetic Algorithm...")
    ga_result  = evolve(
        draw_type    = draw_type,
        seed_tickets = mc_tickets,
        verbose      = False
    )

    ga_ticket  = ga_result["best_ticket"]
    ga_fitness  = float(ga_result["best_fitness"])

    # Pool: MC candidates + GA result + top number combinations
    all_candidates = mc_tickets + [ga_ticket]

    if verbose:
        print(f"  [4/4] Scoring {len(all_candidates)} candidates...")

    scored = [
        score_ticket(t, num_scores)
        for t in all_candidates
    ]
    scored.sort(key=lambda x: x["overall_score"], reverse=True)

    # Top N numbers by combined score for reference
    top_numbers = num_scores.head(15)[
        ["number", "combined_score", "status", "overdue_score"]
    ].to_dict("records")

    return {
        "draw_type":      label,
        "top_numbers":    top_numbers,
        "suggestions":    scored[:n_tickets],
        "ga_ticket":      ga_ticket,
        "ga_fitness":     ga_fitness,
        "ga_breakdown":   ga_result["breakdown"],
        "phase3_reminder": {
            "chi_square_p":       "0.6689 (Lunchtime) / 0.1975 (Teatime)",
            "hot_number_p":       "0.772  — NO predictive power",
            "overdue_p":          "0.541  — NO predictive power",
            "independence_p":     "0.308  — draws are independent",
            "conclusion":         (
                "All statistical tests confirm these draws are random. "
                "No selection method improves your odds. "
                "These suggestions are for entertainment only."
            )
        }
    }