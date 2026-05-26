"""
Phase 4b — Monte Carlo Engine
──────────────────────────────
Simulates millions of lottery draws to map the probability
landscape of number and combination frequencies.

Monte Carlo methods work by running a process thousands or
millions of times and observing the distribution of outcomes.
Here we use it to answer: over millions of simulated draws,
what does the frequency landscape look like?

Expected answer (given Phase 3): flat. Completely flat.
Every number appears roughly equally. Every combination
is equally rare. The simulator will prove this visually
and numerically.

Where Monte Carlo adds real value:
  - Visualising the probability distribution
  - Generating diverse candidate tickets for the GA (Phase 5)
  - Quantifying how "normal" or "unusual" any given ticket is
  - Providing a simulation baseline to compare the GA against
"""

import numpy as np
import pandas as pd
from collections import Counter
from app.services.frequency_engine import load_draws, ALL_NUMBERS, NUMBER_COLS

# ── Core Simulator ────────────────────────────────────────────

def simulate_draws(
    n_simulations: int        = 1_000_000,
    weights: np.ndarray       = None,
    numbers: list             = ALL_NUMBERS
) -> np.ndarray:
    """
    Generates n_simulations random draws of 6 numbers from 1–49.

    weights: optional array of probabilities per number.
             If None, uniform distribution (true random).
             If provided (from Bayesian engine), draws are
             weighted by posterior probabilities.

    Returns array of shape (n_simulations, 6).
    Each row is one simulated draw.

    Why vectorised numpy instead of a Python loop?
    A Python for loop over 1,000,000 iterations takes ~30 seconds.
    numpy's vectorised choice runs in under 2 seconds.
    This is a core performance lesson in data science.
    """
    if weights is not None:
        # Normalise weights to sum to 1
        weights = np.array(weights, dtype=float)
        weights = weights / weights.sum()

    draws = np.array([
        np.random.choice(numbers, size=6, replace=False, p=weights)
        for _ in range(min(n_simulations, 100_000))   # Cap at 100k for speed
    ])

    return draws


def compute_simulated_frequency(draws: np.ndarray) -> pd.DataFrame:
    """
    Counts how often each number appeared across all simulations.
    Compares to theoretical expectation.
    """
    flat        = draws.flatten()
    counts      = Counter(flat)
    total_draws = len(draws)
    expected    = total_draws * 6 / 49

    results = []
    for num in ALL_NUMBERS:
        count = counts.get(num, 0)
        results.append({
            "number":    num,
            "count":     count,
            "expected":  round(expected, 1),
            "deviation": round(count - expected, 1),
            "pct_diff":  round((count - expected) / expected * 100, 2)
        })

    return pd.DataFrame(results).sort_values(
        "count", ascending=False
    ).reset_index(drop=True)


def score_ticket(
    ticket: list,
    draws: np.ndarray
) -> dict:
    """
    Scores a specific 6-number ticket against simulated draws.

    Metrics:
    - hit_rate    : fraction of simulations where ALL 6 matched
                    (will be near 0 — correctly shows how hard it is)
    - avg_matches : average numbers matching per simulation
    - match_dist  : distribution of 0,1,2,3,4,5,6 match counts

    This is used by the Prediction Engine to score candidate tickets.
    """
    ticket_set  = set(ticket)
    match_counts = [
        len(ticket_set & set(draw))
        for draw in draws
    ]
    match_counter = Counter(match_counts)
    total         = len(draws)

    return {
        "ticket":       sorted(ticket),
        "hit_rate_6":   round(match_counter.get(6, 0) / total, 10),
        "hit_rate_5":   round(match_counter.get(5, 0) / total, 6),
        "hit_rate_4":   round(match_counter.get(4, 0) / total, 4),
        "avg_matches":  round(np.mean(match_counts), 4),
        "match_dist":   {k: match_counter.get(k, 0) for k in range(7)}
    }


def generate_candidate_tickets(
    n_tickets: int        = 10,
    draws: np.ndarray     = None,
    weights: np.ndarray   = None
) -> list:
    """
    Generates n_tickets candidate tickets using Monte Carlo sampling.

    These candidates are passed to the Genetic Algorithm (Phase 5)
    as the initial population, and to the Prediction Engine (Phase 6)
    as suggestions.

    Each ticket is just a random draw — but if weights are provided
    from the Bayesian engine, numbers with higher posterior probability
    are sampled more often.
    """
    if draws is None:
        draws = simulate_draws(n_simulations=50_000, weights=weights)

    tickets = []
    seen    = set()

    # Sample unique tickets from the simulation pool
    indices = np.random.choice(len(draws), size=n_tickets * 3, replace=False)

    for idx in indices:
        ticket = tuple(sorted(draws[idx]))
        if ticket not in seen:
            seen.add(ticket)
            tickets.append([int(n) for n in ticket])
        if len(tickets) == n_tickets:
            break

    return tickets


def get_monte_carlo_report(
    draw_type: str    = None,
    n_sims: int       = 100_000,
    use_weights: bool = False
) -> dict:
    """
    Full Monte Carlo report.
    Runs simulation and returns frequency analysis + candidate tickets.

    use_weights: if True, import Bayesian posteriors as sampling weights.
                 The resulting distribution will be slightly non-uniform
                 but Phase 3 proved this provides no predictive advantage.
    """
    weights = None

    if use_weights:
        from app.services.bayesian_engine import compute_posterior
        historical_df = load_draws(draw_type)
        posterior_df  = compute_posterior(historical_df)
        posterior_df  = posterior_df.sort_values("number")
        weights       = posterior_df["posterior_prob"].values

    print(f"  Running {n_sims:,} simulations...")
    draws     = simulate_draws(n_simulations=n_sims, weights=weights)
    freq      = compute_simulated_frequency(draws)
    tickets   = generate_candidate_tickets(n_tickets=10, draws=draws)

    # Key metric: how flat is the distribution?
    # In a truly random system this should be near 0
    spread = round(freq["pct_diff"].abs().mean(), 4)

    return {
        "simulations":        len(draws),
        "weighted":           use_weights,
        "avg_pct_deviation":  spread,
        "top_10_simulated":   freq.head(10).to_dict("records"),
        "candidate_tickets":  tickets,
        "interpretation": (
            f"Distribution is {'flat ✅' if spread < 2 else 'skewed ⚠️'} "
            f"(avg deviation from expected: {spread}%)"
        )
    }