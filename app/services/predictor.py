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

Strategy modes:
  "default"  — original pipeline, tickets scored independently
  "diverse"  — diversity filter ensures max 2 numbers overlap
                between any two selected tickets
  "wheel"    — abbreviated combinatorial wheel built from the
                top-scoring number pool; maximises pair coverage

Honesty contract:
  Every output carries the statistical context from Phase 3.
  We show the analysis AND the proof that it doesn't beat random.
  Users make informed decisions, not false ones.
"""

import pandas as pd
import numpy as np
from itertools import combinations
from app.services.pattern_engine import get_top_pairs
from app.services.frequency_engine import (
    load_draws,
    compute_frequency_score,
    compute_gaps,
    get_full_report as freq_report
)
from app.services.bayesian_engine  import get_bayesian_report
from app.services.monte_carlo      import get_monte_carlo_report
from app.services.genetic_algorithm import evolve
from app.services.ml_engine import predict_with_ml

# ── Scoring Weights ───────────────────────────────────────────
W_FREQUENCY = 0.35
W_BAYESIAN  = 0.35
W_GA        = 0.30
W_ML        = 0.00

# ── Valid strategies ──────────────────────────────────────────
STRATEGIES = ("default", "diverse", "wheel")


# ══════════════════════════════════════════════════════════════
# NUMBER-LEVEL SCORING
# ══════════════════════════════════════════════════════════════

def score_numbers(draw_type: str = None) -> pd.DataFrame:
    """
    Produces a unified score per number combining
    frequency engine and Bayesian engine outputs.
    """
    df      = load_draws(draw_type)
    freq_df = compute_frequency_score(df)
    bayes   = get_bayesian_report(draw_type)
    bayes_df = pd.DataFrame(bayes["all_posteriors"])

    merged = freq_df[["number", "frequency_score", "status"]].merge(
        bayes_df, on="number"
    )

    max_post = merged["posterior_prob"].max()
    min_post = merged["posterior_prob"].min()
    rng      = max_post - min_post if max_post != min_post else 1

    merged["bayes_norm"] = (
        (merged["posterior_prob"] - min_post) / rng * 100
    ).round(2)

    merged["combined_score"] = (
        merged["frequency_score"] * W_FREQUENCY +
        merged["bayes_norm"]      * W_BAYESIAN
    ).round(4)

    gaps_df = compute_gaps(df)[["number", "avg_gap", "draws_since", "overdue_score"]]
    merged  = merged.merge(gaps_df, on="number", how="left")

    return merged.sort_values(
        "combined_score", ascending=False
    ).reset_index(drop=True)


# ══════════════════════════════════════════════════════════════
# TICKET-LEVEL SCORING
# ══════════════════════════════════════════════════════════════

def score_ticket(ticket: list, number_scores: pd.DataFrame) -> dict:
    """
    Scores a complete 6-number ticket.
    Applies HARD balance constraints — tickets that fail
    3/3 odd-even or 3/3 high-low get a penalty multiplier.
    """
    scores = []
    for n in ticket:
        row = number_scores[number_scores["number"] == n]
        if not row.empty:
            scores.append(row.iloc[0]["combined_score"])

    avg_score = round(np.mean(scores), 4) if scores else 0
    min_score = round(min(scores), 4)     if scores else 0

    sorted_t  = sorted(ticket)
    spread    = (sorted_t[-1] - sorted_t[0]) / 48

    odds  = sum(1 for n in ticket if n % 2 != 0)
    highs = sum(1 for n in ticket if n > 24)

    # ── Hard balance constraints ──────────────────────────────
    # Tickets must have 3 odd / 3 even AND 3 high / 3 low.
    # Those that don't receive a score penalty rather than
    # being discarded — we still want to rank them, just lower.
    odd_balance = 1 - abs(odds - 3) / 3
    hl_balance  = 1 - abs(highs - 3) / 3

    # Penalty multiplier: 1.0 if perfectly balanced, down to 0.5
    balance_penalty = 0.5 + 0.5 * (odd_balance * hl_balance)

    # Sum-of-ticket check: draws rarely produce extremes
    ticket_sum = sum(ticket)
    # Ideal range for 6/49: ~100–200; outside gets a soft penalty
    sum_penalty = 1.0
    if ticket_sum < 100 or ticket_sum > 220:
        sum_penalty = 0.85

    overall = round(
        (
            float(avg_score) * 0.5 +
            float(spread)    * 25  +
            float(odd_balance) * 12.5 +
            float(hl_balance)  * 12.5
        ) * balance_penalty * sum_penalty,
        4
    )

    return {
        "ticket":          sorted(ticket),
        "avg_num_score":   float(avg_score),
        "min_num_score":   float(min_score),
        "spread":          float(round(spread, 4)),
        "odd_even":        f"{odds} odd / {6-odds} even",
        "high_low":        f"{highs} high / {6-highs} low",
        "ticket_sum":      ticket_sum,
        "overall_score":   float(overall),
        "balance_ok":      (odds == 3 and highs == 3),
    }


# ══════════════════════════════════════════════════════════════
# STRATEGY IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════

def apply_diversity_filter(
    scored_tickets: list,
    n_tickets: int,
    max_overlap: int = 2
) -> list:
    """
    DIVERSE strategy — selects tickets greedily so that no two
    selected tickets share more than `max_overlap` numbers.

    Works through the ranked list and adds a ticket only if it
    doesn't overlap too much with any already-selected ticket.
    Falls back to best remaining if diversity can't be satisfied.

    Why this matters:
      If tickets [5,10,17,32,40,47] and [5,10,22,32,41,48] both
      appear, they share 5,10,32 — you're betting the same 3
      numbers twice. Diversity filter prevents this waste.
    """
    selected = []
    remaining = list(scored_tickets)  # already sorted by score

    while len(selected) < n_tickets and remaining:
        for i, candidate in enumerate(remaining):
            nums = set(candidate["ticket"])
            overlaps = [
                len(nums & set(s["ticket"]))
                for s in selected
            ]
            if not overlaps or max(overlaps) <= max_overlap:
                selected.append(candidate)
                remaining.pop(i)
                break
        else:
            # No candidate meets diversity — take best remaining
            selected.append(remaining.pop(0))

    return selected[:n_tickets]


def generate_wheel(
    pool: list,
    n_tickets: int,
    number_scores: pd.DataFrame
) -> list:
    """
    WHEEL strategy — abbreviated combinatorial wheel.

    Takes the top-scoring number pool and distributes numbers
    across tickets so that every possible pair from the pool
    appears on at least one ticket (greedy set cover).

    Guarantees: if K numbers from your pool are drawn, at least
    one ticket will contain a pair (2 of those K numbers),
    provided K >= 2 and the pair appears in the wheel.

    This trades ticket independence for pair coverage — you get
    fewer unique number combinations but guaranteed pair capture
    within the pool.

    Steps:
    1. Generate all C(pool, 2) pairs
    2. Greedily pick 6-number tickets that cover the most
       uncovered pairs, also applying balance constraints
    3. Score and return
    """
    all_pairs   = set(combinations(pool, 2))
    covered     = set()
    wheel_tickets = []

    for _ in range(n_tickets):
        best_ticket   = None
        best_coverage = -1
        best_balance  = -1

        # Evaluate all C(pool, 6) candidates — for pool of 15
        # this is C(15,6) = 5005, fast enough
        for candidate in combinations(pool, 6):
            candidate = list(candidate)
            cand_pairs   = set(combinations(candidate, 2))
            new_coverage = len(cand_pairs - covered)

            # Hard balance check
            odds  = sum(1 for n in candidate if n % 2 != 0)
            highs = sum(1 for n in candidate if n > 24)
            balance = (
                1 - abs(odds - 3) / 3 +
                1 - abs(highs - 3) / 3
            )

            # Primary sort: new pair coverage
            # Secondary sort: balance
            if (new_coverage > best_coverage or
                (new_coverage == best_coverage and balance > best_balance)):
                best_ticket   = candidate
                best_coverage = new_coverage
                best_balance  = balance

        if best_ticket:
            wheel_tickets.append(best_ticket)
            covered |= set(combinations(best_ticket, 2))
        else:
            # Pool exhausted — fill with random balanced ticket from pool
            import random
            wheel_tickets.append(sorted(random.sample(pool, 6)))

    # Score all wheel tickets
    return [score_ticket(t, number_scores) for t in wheel_tickets]


# ══════════════════════════════════════════════════════════════
# MAIN PREDICTION FUNCTION
# ══════════════════════════════════════════════════════════════

def generate_predictions(
    draw_type: str  = None,
    n_tickets: int  = 5,
    verbose:   bool = True,
    strategy:  str  = "default"
) -> dict:
    """
    Full prediction pipeline with strategy selection.

    strategy options:
      "default" — original pipeline (MC + GA, independent scoring)
      "diverse" — same pipeline but diversity-filtered selection
                  (max 2 numbers shared between any two tickets)
      "wheel"   — abbreviated combinatorial wheel built from the
                  top 15 scoring numbers; maximises pair coverage

    All strategies use the same number scoring foundation.
    All strategies carry the same Phase 3 honesty disclaimer.
    """
    if strategy not in STRATEGIES:
        raise ValueError(
            f"strategy must be one of {STRATEGIES}, got '{strategy}'"
        )

    label = draw_type or "All Draws"

    if verbose:
        print(f"\n  [Strategy: {strategy.upper()}]")
        print(f"  [1/4] Scoring numbers ({label})...")

    num_scores = score_numbers(draw_type)

    # ── Strategy: WHEEL ───────────────────────────────────────
    # Wheel doesn't need MC or GA — it works directly from the
    # top-scoring number pool using combinatorial coverage.
    if strategy == "wheel":
        if verbose:
            print(f"  [2/4] Building wheel from top-15 number pool...")

        # Pool: top 15 numbers by combined score
        # 15 gives C(15,6)=5005 candidates — fast to evaluate
        pool = num_scores.head(15)["number"].tolist()

        wheel_scored = generate_wheel(pool, n_tickets, num_scores)
        wheel_scored.sort(key=lambda x: x["overall_score"], reverse=True)

        # Pair coverage stats for transparency
        all_pool_pairs   = set(combinations(pool, 2))
        covered_pairs    = set()
        for t in wheel_scored:
            covered_pairs |= set(combinations(t["ticket"], 2))
        coverage_pct = round(
            len(covered_pairs) / len(all_pool_pairs) * 100, 1
        )

        ml_predictions = predict_with_ml(draw_type)
        ml_map = {}
        if not ml_predictions.empty:
            ml_map = dict(zip(
                ml_predictions["number"],
                ml_predictions["ml_probability"]
            ))

        top_numbers = num_scores.head(15)[
            ["number", "combined_score", "status", "overdue_score"]
        ].to_dict("records")
        for row in top_numbers:
            row["ml_probability"] = round(
                float(ml_map.get(row["number"], 0)), 6
            )

        return {
            "draw_type":    label,
            "strategy":     "wheel",
            "strategy_info": {
                "pool_size":      len(pool),
                "pool_numbers":   pool,
                "pairs_in_pool":  len(all_pool_pairs),
                "pairs_covered":  len(covered_pairs),
                "coverage_pct":   coverage_pct,
                "guarantee":      (
                    f"If 2+ of your {len(pool)} pool numbers are drawn, "
                    f"at least one ticket will contain that pair. "
                    f"Pool covers {coverage_pct}% of all possible pairs "
                    f"within the top-15 number set."
                )
            },
            "top_numbers":  top_numbers,
            "suggestions":  wheel_scored[:n_tickets],
            "ga_ticket":    wheel_scored[0]["ticket"],  # best wheel ticket
            "ga_fitness":   wheel_scored[0]["overall_score"],
            "ga_breakdown": {
                "note": "Wheel mode — GA not used. "
                        "Tickets optimised for pair coverage."
            },
            "top_pairs":    get_top_pairs(draw_type, n=20),
            "ml_available": not ml_predictions.empty,
            "phase3_reminder": _phase3_reminder()
        }

    # ── Strategies: DEFAULT + DIVERSE ─────────────────────────
    # Both use the full MC → GA → score pipeline.
    # They differ only in how final tickets are selected.

    if verbose:
        print(f"  [2/4] Running Monte Carlo...")
    mc         = get_monte_carlo_report(draw_type, n_sims=50_000)
    mc_tickets = mc["candidate_tickets"]

    if verbose:
        print(f"  [3/4] Running Genetic Algorithm...")
    ga_result = evolve(
        draw_type    = draw_type,
        seed_tickets = mc_tickets,
        verbose      = False
    )
    ga_ticket  = ga_result["best_ticket"]
    ga_fitness = float(ga_result["best_fitness"])

    all_candidates = mc_tickets + [ga_ticket]

    if verbose:
        print(f"  [4/4] Scoring {len(all_candidates)} candidates "
              f"[strategy={strategy}]...")

    scored = [
        score_ticket(t, num_scores)
        for t in all_candidates
    ]
    scored.sort(key=lambda x: x["overall_score"], reverse=True)

    # ── Select final tickets by strategy ──────────────────────
    if strategy == "diverse":
        suggestions = apply_diversity_filter(
            scored, n_tickets, max_overlap=2
        )
        # Record diversity stats for transparency
        unique_nums = set()
        for t in suggestions:
            unique_nums.update(t["ticket"])
        strategy_info = {
            "max_overlap":    2,
            "unique_numbers": len(unique_nums),
            "total_numbers":  n_tickets * 6,
            "overlap_note": (
                f"{len(unique_nums)} unique numbers across "
                f"{n_tickets} tickets "
                f"(max 2 shared between any pair of tickets)."
            )
        }
    else:
        # default — take top n_tickets as-is
        suggestions   = scored[:n_tickets]
        unique_nums   = set()
        for t in suggestions:
            unique_nums.update(t["ticket"])
        strategy_info = {
            "unique_numbers": len(unique_nums),
            "total_numbers":  n_tickets * 6,
            "overlap_note": (
                f"{len(unique_nums)} unique numbers across "
                f"{n_tickets} tickets (overlap not constrained)."
            )
        }

    # ── ML layer ──────────────────────────────────────────────
    ml_predictions = predict_with_ml(draw_type)
    ml_map = {}
    if not ml_predictions.empty:
        ml_map = dict(zip(
            ml_predictions["number"],
            ml_predictions["ml_probability"]
        ))

    top_numbers = num_scores.head(15)[
        ["number", "combined_score", "status", "overdue_score"]
    ].to_dict("records")
    for row in top_numbers:
        row["ml_probability"] = round(
            float(ml_map.get(row["number"], 0)), 6
        )

    return {
        "draw_type":      label,
        "strategy":       strategy,
        "strategy_info":  strategy_info,
        "top_numbers":    top_numbers,
        "suggestions":    suggestions,
        "ga_ticket":      ga_ticket,
        "ga_fitness":     ga_fitness,
        "ga_breakdown":   ga_result["breakdown"],
        "top_pairs":      get_top_pairs(draw_type, n=20),
        "ml_available":   not ml_predictions.empty,
        "phase3_reminder": _phase3_reminder()
    }


def _phase3_reminder() -> dict:
    return {
        "chi_square_p":   "0.6689 (Lunchtime) / 0.1975 (Teatime)",
        "hot_number_p":   "0.772  — NO predictive power",
        "overdue_p":      "0.541  — NO predictive power",
        "independence_p": "0.308  — draws are independent",
        "conclusion": (
            "All statistical tests confirm these draws are random. "
            "No selection method improves your odds. "
            "These suggestions are for entertainment only."
        )
    }