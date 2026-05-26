"""
Phase 5 — Genetic Algorithm
─────────────────────────────
Evolves a population of candidate tickets toward higher
fitness scores using selection, crossover, and mutation.

IMPORTANT: A higher fitness score does NOT mean higher odds
of winning. Every combination has identical odds (1/13,983,816).

What fitness measures:
  - Statistical balance (spread, odd/even, high/low)
  - Avoidance of common human patterns
  - Alignment with historical frequency data
  - Pair co-occurrence strength

This makes suggestions that are statistically "normal" —
distributed across the number space rather than clustered
in ways humans naturally gravitate toward.
"""

import numpy as np
import pandas as pd
import random
from app.services.frequency_engine import (
    load_draws,
    compute_frequency_score,
    ALL_NUMBERS,
    NUMBER_COLS
)

# ── GA Parameters ─────────────────────────────────────────────

POPULATION_SIZE = 50      # Tickets per generation
N_GENERATIONS   = 100     # Evolution cycles
MUTATION_RATE   = 0.15    # 15% chance of mutation per ticket
ELITE_SIZE      = 10      # Top N survivors kept unchanged
TOURNAMENT_K    = 5       # Tournament selection pool size

# ── Fitness Weights ───────────────────────────────────────────

W_FREQUENCY  = 0.25
W_PAIRS      = 0.20
W_SPREAD     = 0.20
W_ODD_EVEN   = 0.15
W_HIGH_LOW   = 0.15
W_ENTROPY    = 0.05

# ── Ticket Representation ─────────────────────────────────────

def random_ticket() -> list:
    """Generates a single random valid 6-number ticket."""
    return sorted(random.sample(ALL_NUMBERS, 6))


def initialise_population(
    size: int         = POPULATION_SIZE,
    seed_tickets: list = None
) -> list:
    """
    Creates initial population.
    If Monte Carlo candidate tickets are provided as seeds,
    we use them as part of the starting population —
    giving the GA a head start over pure random initialisation.
    """
    population = []

    if seed_tickets:
        for t in seed_tickets[:size // 2]:
            population.append([int(n) for n in t])

    while len(population) < size:
        population.append(random_ticket())

    return population

# ── Fitness Components ────────────────────────────────────────

def spread_score(ticket: list) -> float:
    """
    Rewards tickets whose numbers are evenly spread across 1–49.

    A ticket like [1,2,3,4,5,6] clusters at the bottom — score: low
    A ticket like [4,12,20,31,38,46] spreads evenly — score: high

    Method: divide 1–49 into 6 equal zones. Reward having one
    number per zone (maximum spread).

    Why this matters: human players overselect low numbers
    (birthdays cap at 31). Balanced tickets are statistically
    more "normal" within the full 1–49 space.
    """
    zones     = np.linspace(1, 49, 7)
    zone_hits = [0] * 6

    for n in ticket:
        for i in range(6):
            if zones[i] <= n < zones[i + 1]:
                zone_hits[i] += 1
                break
        else:
            zone_hits[5] += 1   # Catch number 49

    # Perfect spread = one number per zone = max score
    # Penalty for multiple numbers in same zone
    perfect    = 6
    actual     = sum(1 for z in zone_hits if z > 0)
    return actual / perfect


def odd_even_score(ticket: list) -> float:
    """
    Rewards balanced odd/even split.
    Ideal: 3 odd, 3 even → score 1.0
    Worst: all odd or all even → score 0.0

    Historical draws show roughly 50/50 odd/even distribution —
    consistent with randomness. Tickets matching this are
    statistically "normal."
    """
    odds  = sum(1 for n in ticket if n % 2 != 0)
    evens = 6 - odds
    # Distance from perfect 3/3 split, normalised
    imbalance = abs(odds - evens) / 6
    return 1.0 - imbalance


def high_low_score(ticket: list) -> float:
    """
    Rewards balanced high(25–49)/low(1–24) split.
    Ideal: 3 high, 3 low → score 1.0

    Same reasoning as odd/even — random draws are roughly
    balanced. Human selections skew low (birthdays).
    """
    lows  = sum(1 for n in ticket if n <= 24)
    highs = 6 - lows
    imbalance = abs(lows - highs) / 6
    return 1.0 - imbalance


def entropy_score(ticket: list) -> float:
    """
    Penalises consecutive numbers and common human patterns.

    [1,2,3,4,5,6] has 5 consecutive pairs → very low entropy
    [5,17,23,38,44,49] has 0 consecutive pairs → high entropy

    Also penalises all numbers under 31 (birthday bias).
    """
    ticket  = sorted(ticket)
    # Count consecutive pairs
    consec  = sum(1 for i in range(5) if ticket[i+1] - ticket[i] == 1)
    # Count numbers ≤ 31 (birthday range)
    bday    = sum(1 for n in ticket if n <= 31)

    consec_penalty = consec / 5          # 0 = no consecutive, 1 = all consecutive
    bday_penalty   = max(0, bday - 3) / 3  # Penalty only if more than 3 birthdays

    return 1.0 - (consec_penalty * 0.6 + bday_penalty * 0.4)


def pair_score(ticket: list, pair_counts: dict) -> float:
    """
    Rewards tickets containing number pairs that frequently
    co-occur in historical draws.

    pair_counts: dict of {(n1,n2): count} from historical data

    If pair (7,23) appeared 42 times and (12,15) appeared 8 times,
    a ticket containing (7,23) scores higher than one with (12,15).
    """
    if not pair_counts:
        return 0.5   # Neutral if no pair data

    ticket_pairs = []
    nums         = sorted(ticket)
    for i in range(len(nums)):
        for j in range(i+1, len(nums)):
            ticket_pairs.append((nums[i], nums[j]))

    scores = [pair_counts.get(pair, 0) for pair in ticket_pairs]
    if not scores or max(scores) == 0:
        return 0.5

    return min(sum(scores) / (len(scores) * max(pair_counts.values())), 1.0)


def frequency_fitness(ticket: list, freq_scores: dict) -> float:
    """
    Rewards tickets containing historically frequent numbers.
    freq_scores: {number: normalised_score} from frequency engine.
    """
    if not freq_scores:
        return 0.5
    scores = [freq_scores.get(n, 0) for n in ticket]
    return sum(scores) / (6 * 100)   # Normalise: scores are 0–100


def compute_fitness(
    ticket: list,
    freq_scores: dict,
    pair_counts: dict
) -> float:
    """
    Weighted combination of all fitness components.
    Returns a score between 0.0 and 1.0.

    Remember: higher score = more statistically balanced ticket.
    Higher score does NOT mean higher winning probability.
    """
    f_freq    = frequency_fitness(ticket, freq_scores)
    f_pairs   = pair_score(ticket, pair_counts)
    f_spread  = spread_score(ticket)
    f_oddeven = odd_even_score(ticket)
    f_highlow = high_low_score(ticket)
    f_entropy = entropy_score(ticket)

    return (
        f_freq    * W_FREQUENCY +
        f_pairs   * W_PAIRS     +
        f_spread  * W_SPREAD    +
        f_oddeven * W_ODD_EVEN  +
        f_highlow * W_HIGH_LOW  +
        f_entropy * W_ENTROPY
    )

# ── Genetic Operators ─────────────────────────────────────────

def tournament_select(
    population: list,
    fitnesses: list,
    k: int = TOURNAMENT_K
) -> list:
    """
    Tournament selection: randomly pick k tickets, return the fittest.

    This is better than always picking the single best ticket
    because it maintains genetic diversity — avoiding premature
    convergence where all tickets look the same.
    """
    indices  = random.sample(range(len(population)), k)
    best_idx = max(indices, key=lambda i: fitnesses[i])
    return population[best_idx]


def crossover(parent1: list, parent2: list) -> list:
    """
    Creates a child ticket by combining two parent tickets.

    Method: take the union of both parents' numbers, then
    randomly select 6 from the combined pool.

    This preserves "good genes" (numbers) from both parents
    while creating genuinely new combinations.

    Example:
      Parent1: [3, 12, 23, 34, 41, 47]
      Parent2: [7, 12, 19, 34, 38, 46]
      Union:   [3, 7, 12, 19, 23, 34, 38, 41, 46, 47]
      Child:   [7, 12, 23, 34, 41, 46]   ← 6 sampled from union
    """
    combined = list(set(parent1) | set(parent2))
    if len(combined) < 6:
        return random_ticket()
    return sorted(random.sample(combined, 6))


def mutate(ticket: list, rate: float = MUTATION_RATE) -> list:
    """
    With probability `rate`, replaces one number in the ticket
    with a new random number not already in the ticket.

    Mutation prevents the population from converging too quickly
    and ensures we explore the full search space.
    """
    if random.random() > rate:
        return ticket   # No mutation

    ticket   = ticket.copy()
    remove   = random.choice(ticket)
    ticket.remove(remove)

    available = [n for n in ALL_NUMBERS if n not in ticket]
    ticket.append(random.choice(available))

    return sorted(ticket)

# ── Evolution Loop ────────────────────────────────────────────

def evolve(
    draw_type: str    = None,
    seed_tickets: list = None,
    verbose: bool     = True
) -> dict:
    """
    Main GA loop — runs for N_GENERATIONS and returns the
    fittest ticket found, along with evolution history.

    Steps each generation:
    1. Evaluate fitness of every ticket
    2. Keep top ELITE_SIZE unchanged (elitism)
    3. Fill remaining slots via tournament select + crossover
    4. Apply mutation to non-elite tickets
    5. Record best fitness for this generation
    """

    # ── Precompute lookup tables ──────────────────────────────
    df = load_draws(draw_type)

    # Frequency scores: {number: score 0–100}
    freq_df     = compute_frequency_score(df)
    freq_scores = dict(zip(
        freq_df["number"],
        freq_df["frequency_score"]
    ))

    # Pair co-occurrence counts: {(n1,n2): count}
    pair_counts = {}
    for _, row in df.iterrows():
        nums = sorted([int(row[c]) for c in NUMBER_COLS])
        for i in range(len(nums)):
            for j in range(i+1, len(nums)):
                pair = (nums[i], nums[j])
                pair_counts[pair] = pair_counts.get(pair, 0) + 1

    # ── Initialise population ─────────────────────────────────
    population = initialise_population(
        size=POPULATION_SIZE,
        seed_tickets=seed_tickets
    )

    best_ticket   = None
    best_fitness  = -1
    history       = []   # Tracks best fitness per generation

    # ── Generation loop ───────────────────────────────────────
    for gen in range(N_GENERATIONS):

        # Evaluate all tickets
        fitnesses = [
            compute_fitness(t, freq_scores, pair_counts)
            for t in population
        ]

        # Track overall best
        gen_best_idx = np.argmax(fitnesses)
        gen_best_fit = fitnesses[gen_best_idx]
        history.append(round(gen_best_fit, 6))

        if gen_best_fit > best_fitness:
            best_fitness = gen_best_fit
            best_ticket  = population[gen_best_idx].copy()

        if verbose and (gen % 20 == 0 or gen == N_GENERATIONS - 1):
            print(f"    Gen {gen+1:3d}/{N_GENERATIONS} "
                  f"| Best fitness: {gen_best_fit:.4f} "
                  f"| Ticket: {population[gen_best_idx]}")

        # Elite — carry top tickets unchanged
        sorted_pairs = sorted(
            zip(fitnesses, population),
            key=lambda x: x[0],
            reverse=True
        )
        new_population = [t for _, t in sorted_pairs[:ELITE_SIZE]]

        # Fill rest via selection + crossover + mutation
        while len(new_population) < POPULATION_SIZE:
            p1    = tournament_select(population, fitnesses)
            p2    = tournament_select(population, fitnesses)
            child = crossover(p1, p2)
            child = mutate(child)
            new_population.append(child)

        population = new_population

    # ── Fitness breakdown for best ticket ─────────────────────
    breakdown = {
        "frequency":  round(frequency_fitness(best_ticket, freq_scores), 4),
        "pairs":      round(pair_score(best_ticket, pair_counts), 4),
        "spread":     round(spread_score(best_ticket), 4),
        "odd_even":   round(odd_even_score(best_ticket), 4),
        "high_low":   round(high_low_score(best_ticket), 4),
        "entropy":    round(entropy_score(best_ticket), 4),
    }

    return {
        "draw_type":      draw_type or "All Draws",
        "best_ticket":    best_ticket,
        "best_fitness":   round(best_fitness, 6),
        "fitness_history": history,
        "breakdown":      breakdown,
        "generations":    N_GENERATIONS,
        "population_size": POPULATION_SIZE,
        "disclaimer": (
            "This ticket was optimised for statistical balance, "
            "NOT for winning probability. All combinations have "
            "identical odds of 1 in 13,983,816."
        )
    }