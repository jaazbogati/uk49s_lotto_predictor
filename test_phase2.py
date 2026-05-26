from app.services.frequency_engine import get_full_report
import json

print("\n📊 Running Frequency Analysis...\n")

# Test Lunchtime
report = get_full_report(draw_type="Lunchtime")

print(f"Draw type   : {report['label']}")
print(f"Total draws : {report['total_draws']}")
print(f"Date range  : {report['date_range']['from']} → {report['date_range']['to']}")
print(f"\n🔥 Hot numbers  : {report['hot_numbers']}")
print(f"🧊 Cold numbers : {report['cold_numbers']}")
print(f"\n⏰ Most overdue numbers:")
for row in report['overdue'][:5]:
    print(f"   Number {row['number']:2d} → avg gap: {row['avg_gap']} draws | "
          f"draws since last: {row['draws_since']} | "
          f"overdue score: {row['overdue_score']}")

print(f"\n📈 Top 10 by frequency score:")
for row in report['scores'][:10]:
    print(f"   Number {row['number']:2d} → score: {row['frequency_score']} {row['status']}")