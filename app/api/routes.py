"""
API Routes
───────────
All endpoints follow the same pattern:
  1. Accept draw_type as a path parameter ("Lunchtime" or "Teatime")
  2. Call the relevant engine function
  3. Return structured JSON

Error handling wraps every engine call — if an engine fails,
the API returns a clean error message rather than a stack trace.
"""

from fastapi  import APIRouter, HTTPException, BackgroundTasks
from typing   import Optional
from app.core.database import SessionLocal
from app.models.draw_model import Draw

router = APIRouter()

# ── Helper ────────────────────────────────────────────────────

def validate_draw_type(draw_type: str) -> str:
    """
    Normalises and validates the draw_type parameter.
    Accepts "lunchtime" or "teatime" (case-insensitive).
    Returns the capitalised version the engines expect.
    """
    valid = {"lunchtime": "Lunchtime", "teatime": "Teatime"}
    key   = draw_type.lower()
    if key not in valid:
        raise HTTPException(
            status_code = 422,
            detail      = f"draw_type must be 'lunchtime' or 'teatime', got '{draw_type}'"
        )
    return valid[key]

# ── Health ────────────────────────────────────────────────────

@router.get("/health")
def health():
    """Basic health check — confirms API is running and DB is reachable."""
    try:
        db    = SessionLocal()
        count = db.query(Draw).count()
        db.close()
        return {
            "status":      "healthy",
            "draws_in_db": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Latest Results ────────────────────────────────────────────

@router.get("/latest")
def latest_results(limit: int = 20):
    """
    Returns the most recent draws from the database.
    Used by the React frontend to display recent history.
    """
    try:
        db   = SessionLocal()
        rows = (
            db.query(Draw)
            .order_by(Draw.date.desc())
            .limit(limit)
            .all()
        )
        db.close()

        return {
            "count":   len(rows),
            "results": [
                {
                    "date":      str(r.date),
                    "draw_type": r.draw_type,
                    "numbers":   [r.n1, r.n2, r.n3, r.n4, r.n5, r.n6],
                    "booster":   r.booster
                }
                for r in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Frequency Stats ───────────────────────────────────────────

@router.get("/stats/{draw_type}")
def frequency_stats(draw_type: str):
    """
    Returns the full Phase 2 frequency report for a draw type.
    Includes hot/cold numbers, gaps, overdue scores, frequency scores.
    """
    draw = validate_draw_type(draw_type)
    try:
        from app.services.frequency_engine import get_full_report
        return get_full_report(draw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Statistical Analysis ──────────────────────────────────────

@router.get("/analysis/{draw_type}")
def statistical_analysis(draw_type: str):
    """
    Returns Phase 3 statistical test results.
    Chi-square, hot number test, overdue test.
    Note: chi-square and independence tests are fast.
    Hot number and overdue tests are cached after first run.
    """
    draw = validate_draw_type(draw_type)
    try:
        from app.services.stats_engine import (
            test_randomness,
            test_draw_independence
        )
        return {
            "randomness_test":   test_randomness(draw),
            "independence_test": test_draw_independence()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Number Scores ─────────────────────────────────────────────

@router.get("/numbers/{draw_type}")
def number_scores(draw_type: str, limit: int = 49):
    """
    Returns all 49 numbers ranked by combined score.
    Combines frequency engine and Bayesian engine outputs.
    Used by the React frontend for the number heatmap.
    """
    draw = validate_draw_type(draw_type)
    try:
        from app.services.predictor import score_numbers
        df = score_numbers(draw)

        return {
            "draw_type": draw,
            "numbers":   df[[
                "number", "combined_score", "status",
                "overdue_score", "draws_since", "avg_gap"
            ]].head(limit).to_dict("records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Predictions ───────────────────────────────────────────────

@router.get("/predictions/{draw_type}")
def predictions(draw_type: str, n_tickets: int = 5):
    """
    Runs the full Phase 6 prediction pipeline and returns
    top ticket suggestions for the requested draw type.

    This endpoint takes ~60 seconds because it runs:
      - Monte Carlo (50k simulations)
      - Genetic Algorithm (100 generations)
      - Candidate scoring

    In Phase 10 we'll add caching so results are pre-computed.
    """
    draw = validate_draw_type(draw_type)
    try:
        from app.services.predictor import generate_predictions
        return generate_predictions(
            draw_type = draw,
            n_tickets = n_tickets,
            verbose   = False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Manual Scrape Trigger ─────────────────────────────────────

@router.post("/scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    """
    Triggers a manual scrape in the background.
    Returns immediately — scrape runs asynchronously.
    Use GET /health to see updated draw count when done.
    """
    try:
        from app.services.scraper import run_scraper
        background_tasks.add_task(run_scraper)
        return {
            "status":  "started",
            "message": "Scrape running in background. Check /health for updated count."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# ── Backtest ──────────────────────────────────────────────────

@router.get("/backtest/{draw_type}")
def run_backtest(
    draw_type:    str,
    window:       int = 200,
    sample_every: int = 10
):
    """
    Runs walk-forward backtest. Takes 2–5 minutes.
    Returns model vs random hit rates across all historical draws.
    """
    draw = validate_draw_type(draw_type)
    try:
        from app.services.backtester import backtest
        return backtest(
            draw_type    = draw,
            window       = window,
            sample_every = sample_every,
            verbose      = False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Track Record ──────────────────────────────────────────────

@router.get("/track-record/{draw_type}")
def track_record(draw_type: str):
    """
    Returns real-world performance of logged predictions.
    Grows over time as predictions are generated and scored.
    """
    draw = validate_draw_type(draw_type)
    try:
        from app.services.outcome_tracker import get_track_record
        return get_track_record(draw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Score Pending ─────────────────────────────────────────────

@router.post("/score-pending")
def score_pending(background_tasks: BackgroundTasks):
    """
    Scores all pending predictions whose draw date has passed.
    Run this daily — or trigger manually from the dashboard.
    """
    try:
        from app.services.outcome_tracker import score_pending_predictions
        background_tasks.add_task(score_pending_predictions)
        return {"status": "started", "message": "Scoring pending predictions in background."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))