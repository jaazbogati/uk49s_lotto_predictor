from app.services.outcome_tracker import get_track_record, score_pending_predictions

print("Testing outcome tracker...")
print("Scoring any pending predictions...")

result = score_pending_predictions()
print(f"  Pending found: {result['pending_found']}")
print(f"  Scored:        {result['scored']}")
print(f"  Missed:        {result['missed']}")

record = get_track_record("Lunchtime")
print(f"  Track record rows: {record['total_scored']}")
print("✅ Outcome tracker working")