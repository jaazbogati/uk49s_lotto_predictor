"""
Outcome Tracker
────────────────
Scores logged predictions against actual draw results.

Key design decision:
  predicted_pairs is stored on the FIRST ticket of each draw/date group only.
  All tickets for the same draw share the same pair prediction set.
  Pair scoring happens once per draw, not once per ticket.
"""

from datetime import date
from sqlalchemy import and_
from sqlalchemy.orm.attributes import flag_modified
from app.core.database import SessionLocal
from app.models.draw_model import Draw
from app.models.prediction_log import PredictionLog, PredictionStatus
from app.services.pattern_engine import check_pair_hits


def _normalise_draw_type(draw_type: str) -> str:
    """Always returns 'Lunchtime' or 'Teatime' regardless of input casing."""
    mapping = {"lunchtime": "Lunchtime", "teatime": "Teatime"}
    return mapping.get(draw_type.lower(), draw_type)


def _clean_pairs(predicted_pairs: list) -> list:
    """
    Serialises predicted pairs to plain dicts with n1/n2/pair keys.
    Handles both full dicts from get_top_pairs() and raw tuples/lists.
    """
    if not predicted_pairs:
        return None
    clean = []
    for p in predicted_pairs:
        if isinstance(p, dict) and "n1" in p and "n2" in p:
            # Already the right shape from get_top_pairs()
            clean.append({
                "pair":  str(p.get("pair", f"{p['n1']}-{p['n2']}")),
                "n1":    int(p["n1"]),
                "n2":    int(p["n2"]),
                "count": int(p.get("count", 0)),
                "score": float(p.get("score", 0)),
            })
        elif isinstance(p, dict) and "pair" in p and isinstance(p["pair"], list):
            # Fallback: {"pair": [3, 7]}
            n1, n2 = int(p["pair"][0]), int(p["pair"][1])
            clean.append({"pair": f"{n1}-{n2}", "n1": n1, "n2": n2, "count": 0, "score": 0})
        elif isinstance(p, (list, tuple)) and len(p) == 2:
            # Raw tuple/list pair
            n1, n2 = int(p[0]), int(p[1])
            clean.append({"pair": f"{n1}-{n2}", "n1": n1, "n2": n2, "count": 0, "score": 0})
    return clean if clean else None


def log_predictions(
    draw_type:       str,
    draw_date:       date,
    suggestions:     list,
    ga_fitness:      float = None,
    predicted_pairs: list  = None
) -> int:
    """
    Saves predictions to the prediction log.

    predicted_pairs is stored on the first ticket only.
    Remaining tickets for the same draw set predicted_pairs=None
    to avoid redundant storage — scoring reads the first ticket's pairs.
    """
    db       = SessionLocal()
    logged   = 0
    draw_type = _normalise_draw_type(draw_type)
    pairs    = _clean_pairs(predicted_pairs)

    try:
        for i, s in enumerate(suggestions):
            clean_score  = float(s.get("overall_score")) if s.get("overall_score") is not None else None
            clean_fit    = float(ga_fitness) if ga_fitness is not None else None
            clean_ticket = [int(n) for n in s["ticket"]]

            entry = PredictionLog(
                draw_date       = draw_date,
                draw_type       = draw_type,
                ticket          = clean_ticket,
                ga_fitness      = clean_fit,
                overall_score   = clean_score,
                # Store pairs on first ticket only — one set per draw session
                predicted_pairs = pairs if i == 0 else None,
                status          = PredictionStatus.PENDING
            )
            db.add(entry)
            logged += 1

        db.commit()
        print(f"  [LOG] Saved {logged} predictions for {draw_type} {draw_date} "
              f"({'with' if pairs else 'without'} pairs)")

    except Exception as e:
        db.rollback()
        print(f"  [LOG ERROR] {e}")
        raise
    finally:
        db.close()

    return logged


def score_pending_predictions() -> dict:
    """
    Scores all PENDING predictions whose draw date has passed.

    Pair scoring:
      - Finds the first ticket in each draw/date group that has predicted_pairs
      - Scores pairs once against the actual draw numbers
      - Applies that result to ALL tickets in the same draw/date/type group
    """
    db      = SessionLocal()
    today   = date.today()
    scored  = 0
    missed  = 0
    pending = []

    try:
        pending = db.query(PredictionLog).filter(
            and_(
                PredictionLog.status    == PredictionStatus.PENDING,
                PredictionLog.draw_date <=  today
            )
        ).order_by(PredictionLog.draw_date, PredictionLog.draw_type, PredictionLog.id).all()

        print(f"  [TRACKER] Found {len(pending)} pending predictions to score")

        # Group by (draw_date, draw_type) so we look up each actual draw once
        # and score pairs once per group
        from itertools import groupby
        key_fn = lambda r: (r.draw_date, r.draw_type)

        for (draw_date, draw_type), group in groupby(pending, key=key_fn):
            group = list(group)

            # Look up the actual draw result once per group
            actual = db.query(Draw).filter(
                and_(
                    Draw.date      == draw_date,
                    Draw.draw_type == draw_type
                )
            ).first()

            if not actual:
                for pred in group:
                    pred.status = PredictionStatus.MISSED
                    missed += len(group)
                continue

            actual_numbers = sorted([
                actual.n1, actual.n2, actual.n3,
                actual.n4, actual.n5, actual.n6
            ])
            actual_set = set(actual_numbers)

            # Score pairs once for this draw group —
            # find the ticket that has predicted_pairs stored
            pair_result = None
            for pred in group:
                if pred.predicted_pairs:
                    pair_result = check_pair_hits(
                        pred.predicted_pairs,
                        actual_numbers   # list, not set
                    )
                    break   # only need to score once

            # Score every ticket in the group
            for pred in group:
                ticket_set  = set(pred.ticket)
                hits        = len(ticket_set & actual_set)
                booster_hit = 1 if actual.booster in ticket_set else 0

                pred.actual_numbers = actual_numbers
                pred.actual_booster = actual.booster
                pred.hits           = hits
                pred.booster_hit    = booster_hit
                pred.pair_hits      = pair_result   # same result for all tickets in group
                pred.status         = PredictionStatus.SCORED

                flag_modified(pred, "pair_hits")
                flag_modified(pred, "actual_numbers")
                scored += 1

        db.commit()
        print(f"  [TRACKER] Scored {scored}, missed {missed}")

    except Exception as e:
        db.rollback()
        print(f"  [TRACKER ERROR] {e}")
        raise
    finally:
        db.close()

    return {
        "pending_found": len(pending),
        "scored":        scored,
        "missed":        missed
    }


def get_track_record(draw_type: str = None) -> dict:
    """
    Returns the full historical track record.
    draw_type is already capitalised when called from routes.py.
    """
    db = SessionLocal()

    try:
        query = db.query(PredictionLog).filter(
            PredictionLog.status == PredictionStatus.SCORED
        )
        if draw_type:
            query = query.filter(PredictionLog.draw_type == draw_type)

        rows = query.order_by(PredictionLog.draw_date.desc()).all()

    finally:
        db.close()

    if not rows:
        return {
            "total_scored":       0,
            "recent_predictions": [],
            "message": (
                "No scored predictions yet. "
                "Generate predictions daily to build a track record."
            )
        }

    hits_list = [r.hits for r in rows if r.hits is not None]
    hit_dist  = {str(k): sum(1 for h in hits_list if h == k) for k in range(7)}
    avg       = round(sum(hits_list) / len(hits_list), 4) if hits_list else 0

    recent = [
        {
            "date":          str(r.draw_date),
            "draw_type":     r.draw_type,
            "ticket":        r.ticket,
            "actual":        r.actual_numbers,
            "hits":          r.hits,
            "booster_hit":   r.booster_hit,
            "overall_score": r.overall_score,
            # pair_hits only present on first ticket of each group
            "pair_hits":     r.pair_hits,
        }
        for r in rows[:30]
    ]

    return {
        "draw_type":          draw_type or "All",
        "total_scored":       len(rows),
        "avg_hits":           avg,
        "random_baseline":    round(6 * 6 / 49, 4),
        "hit_distribution":   hit_dist,
        "recent_predictions": recent,
        "interpretation": (
            f"Average hits: {round(avg, 2)} vs random baseline of "
            f"{round(6*6/49, 2)}. Total scored: {len(rows)}."
        )
    }