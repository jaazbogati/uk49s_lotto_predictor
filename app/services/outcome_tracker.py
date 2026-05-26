"""
Outcome Tracker
────────────────
Scores logged predictions against actual draw results.

Every time the prediction engine generates suggestions,
they can be saved to prediction_log with status=PENDING.

This service runs after each draw and:
  1. Finds all PENDING predictions for that draw date/type
  2. Looks up the actual result in the draws table
  3. Scores each ticket (how many numbers matched?)
  4. Updates the log with hits, booster_hit, and status=SCORED

Over time this builds a genuine real-world track record.
"""

from datetime import date, timedelta
from sqlalchemy import and_
from app.core.database import SessionLocal
from app.models.draw_model import Draw
from app.models.prediction_log import PredictionLog, PredictionStatus
import pandas as pd


def log_predictions(
    draw_type:    str,
    draw_date:    date,
    suggestions:  list,
    ga_fitness:   float = None
) -> int:
    db      = SessionLocal()
    logged  = 0

    try:
        for s in suggestions:
            # Force all numeric values to plain Python types
            # np.float64 causes PostgreSQL schema errors
            raw_score  = s.get("overall_score")
            raw_fit    = ga_fitness

            clean_score = float(raw_score) if raw_score is not None else None
            clean_fit   = float(raw_fit)   if raw_fit   is not None else None
            clean_ticket = [int(n) for n in s["ticket"]]

            entry = PredictionLog(
                draw_date     = draw_date,
                draw_type     = draw_type,
                ticket        = clean_ticket,
                ga_fitness    = clean_fit,
                overall_score = clean_score,
                status        = PredictionStatus.PENDING
            )
            db.add(entry)
            logged += 1

        db.commit()
        print(f"  [LOG] Saved {logged} predictions for {draw_type} {draw_date}")

    except Exception as e:
        db.rollback()
        print(f"  [LOG ERROR] {e}")
    finally:
        db.close()

    return logged


def score_pending_predictions() -> dict:
    """
    Finds all PENDING predictions whose draw date has passed,
    looks up the actual result, and scores each ticket.

    Run this daily after draws complete.
    Returns summary of what was scored.
    """
    db      = SessionLocal()
    today   = date.today()
    scored  = 0
    missed  = 0

    try:
        # Find all pending predictions where draw date has passed
        pending = db.query(PredictionLog).filter(
            and_(
                PredictionLog.status   == PredictionStatus.PENDING,
                PredictionLog.draw_date < today
            )
        ).all()

        print(f"  [TRACKER] Found {len(pending)} pending predictions to score")

        for pred in pending:
            # Look up actual draw result
            actual = db.query(Draw).filter(
                and_(
                    Draw.date      == pred.draw_date,
                    Draw.draw_type == pred.draw_type
                )
            ).first()

            if not actual:
                pred.status = PredictionStatus.MISSED
                missed += 1
                continue

            # Score the ticket
            actual_numbers = {actual.n1, actual.n2, actual.n3,
                              actual.n4, actual.n5, actual.n6}
            ticket_set     = set(pred.ticket)
            hits           = len(ticket_set & actual_numbers)
            booster_hit    = 1 if actual.booster in ticket_set else 0

            # Update the record
            pred.actual_numbers = sorted(actual_numbers)
            pred.actual_booster = actual.booster
            pred.hits           = hits
            pred.booster_hit    = booster_hit
            pred.status         = PredictionStatus.SCORED
            scored += 1

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"  [TRACKER ERROR] {e}")
    finally:
        db.close()

    return {
        "pending_found": len(pending) if 'pending' in locals() else 0,
        "scored":        scored,
        "missed":        missed
    }


def get_track_record(draw_type: str = None) -> dict:
    """
    Returns the full historical track record of logged predictions.
    Used by the API and dashboard to show real-world performance.
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
            "total_scored": 0,
            "message":      "No scored predictions yet. Generate predictions daily to build a track record."
        }

    hits_list = [r.hits for r in rows if r.hits is not None]

    # Hit distribution
    hit_dist = {str(k): sum(1 for h in hits_list if h == k) for k in range(7)}

    # Recent 30 predictions
    recent = [
        {
            "date":           str(r.draw_date),
            "draw_type":      r.draw_type,
            "ticket":         r.ticket,
            "actual":         r.actual_numbers,
            "hits":           r.hits,
            "booster_hit":    r.booster_hit,
            "overall_score":  r.overall_score
        }
        for r in rows[:30]
    ]

    return {
        "draw_type":     draw_type or "All",
        "total_scored":  len(rows),
        "avg_hits":      round(sum(hits_list) / len(hits_list), 4) if hits_list else 0,
        "random_baseline": round(6 * 6 / 49, 4),  # Expected hits from random
        "hit_distribution": hit_dist,
        "recent_predictions": recent,
        "interpretation": (
            f"Average hits: {round(sum(hits_list)/len(hits_list),2) if hits_list else 0} "
            f"vs random baseline of {round(6*6/49,2)}. "
            f"Total predictions scored: {len(rows)}."
        )
    }