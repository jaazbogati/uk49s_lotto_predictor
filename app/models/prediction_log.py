"""
Prediction Log — tracks every suggestion made by the engine.

When a prediction is generated, we store it here with a status
of "pending". When that draw date passes, the outcome tracker
scores it against the actual result and updates the record.

This gives the app a real, growing track record over time.
"""

from sqlalchemy import (
    Column, Integer, String, Date, Float,
    DateTime, JSON, Enum as SAEnum
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class PredictionStatus(str, enum.Enum):
    PENDING  = "pending"    # Draw hasn't happened yet
    SCORED   = "scored"     # Draw happened, result recorded
    MISSED   = "missed"     # Draw happened, no match data found


class PredictionLog(Base):
    """
    One row per ticket suggestion.
    Multiple rows per draw date (one per suggested ticket).
    """
    __tablename__ = "prediction_log"

    id            = Column(Integer, primary_key=True, index=True)
    created_at    = Column(DateTime, server_default=func.now())
    draw_date     = Column(Date, nullable=False)
    draw_type     = Column(String(20), nullable=False)

    # The suggested ticket as JSON array e.g. [3, 12, 20, 31, 38, 45]
    ticket        = Column(JSON, nullable=False)

    # Engine metadata
    ga_fitness    = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)

    # Outcome — filled in by outcome_tracker after the draw
    status        = Column(
        SAEnum(PredictionStatus),
        default=PredictionStatus.PENDING,
        nullable=False
    )
    actual_numbers = Column(JSON, nullable=True)    # What actually came up
    actual_booster = Column(Integer, nullable=True)
    hits           = Column(Integer, nullable=True) # 0–6 matches
    booster_hit    = Column(Integer, default=0)     # 1 if booster matched
    #Pairing hits (for pattern engine analysis)
    predicted_pairs = Column(JSON, nullable=True)   # The 20 predicted pairs
    pair_hits       = Column(JSON, nullable=True)   # Results after scoring

    def __repr__(self):
        return (
            f"<PredictionLog {self.draw_date} {self.draw_type} "
            f"ticket={self.ticket} hits={self.hits} status={self.status}>"
        )