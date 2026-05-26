from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from app.core.database import Base

class Draw(Base):

    """
    Represents a lottery draw in the database.

    *__tablename__* tells SQLAlchemy what to call the tables in PostgrSQL.

    The UniqueConstraint ensures we don't accidentally insert the same draw twice.
    """
    __tablename__ = "draws"

    id          = Column(Integer, primary_key=True, index=True)
    date        = Column(DateTime, nullable=False)
    draw_type   = Column(String(20), nullable=False)  # Lunchtime or Teatime
    source      = Column(String(50), nullable=False)  # Which site we scraped this from
    n1          = Column(Integer, nullable=False)
    n2          = Column(Integer, nullable=False)        
    n3          = Column(Integer, nullable=False)
    n4          = Column(Integer, nullable=False)
    n5          = Column(Integer, nullable=False)
    n6          = Column(Integer, nullable=False)
    booster     = Column(Integer, nullable=True)  # Booster number, if applicable

    __table_args__ = (UniqueConstraint('date', 'draw_type', name='uq_draw_date_type'),)

    def __repr__(self):
        return (
            f"<Draw {self.date.date()} {self.draw_type} "
            f"[{self.n1}, {self.n2}, {self.n3}, {self.n4}, {self.n5}, {self.n6}] "
            f"B:{self.booster}>"
        )