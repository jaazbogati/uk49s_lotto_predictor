from app.core.database import SessionLocal
from app.models.draw_model import Draw
from app.models.prediction_log import PredictionLog

db    = SessionLocal()
draws = db.query(Draw).count()
preds = db.query(PredictionLog).count()
db.close()

print(f"✅ Database connected")
print(f"   Draws in DB:       {draws}")
print(f"   Predictions in DB: {preds}")