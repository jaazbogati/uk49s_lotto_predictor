from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import DATABASE_URL

#The engine is the actual connection to PostgrSQL
engine = create_engine(DATABASE_URL, echo=False)

#A session is how we send queries - open one, use it, close it
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

#All our table models will inherit from this base
Base = declarative_base()


def get_db():
    """
    Dependency for FastAPI routes - provides a database session that is
    automatically closed after the request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Creates all tables that dont exist yet, in the database based on our models. Run this once before
    starting the app to set up the database. Safe to run multiple times - it will only create missing tables.
    """
    from app.models import draw_model, prediction_log #noqa: F401 - import triggers table registration
    Base.metadata.create_all(bind=engine)
    print("[DB] Tables created or already exist.")