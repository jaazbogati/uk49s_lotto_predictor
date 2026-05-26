from app.services.predictor import generate_predictions

print("\n🎯 Phase 6 — Prediction Engine\n")
print("=" * 60)

for draw in ["Lunchtime", "Teatime"]:
    print(f"\n{'─'*60}")
    print(f"  Draw: {draw}")
    print(f"{'─'*60}")

    result = generate_predictions(draw_type=draw, n_tickets=5)

    print(f"\n  📊 Top 10 Numbers by Combined Score:")
    for r in result["top_numbers"][:10]:
        print(f"    {r['number']:2d} → score: {r['combined_score']:.2f}  "
              f"{r['status']}  "
              f"overdue: {r['overdue_score']}")

    print(f"\n  🎟️  Top 5 Suggested Tickets:")
    for i, t in enumerate(result["suggestions"], 1):
        print(f"\n    Ticket {i}: {t['ticket']}")
        print(f"      Score    : {t['overall_score']}")
        print(f"      Odd/Even : {t['odd_even']}")
        print(f"      High/Low : {t['high_low']}")

    print(f"\n  🧬 GA Best Ticket : {result['ga_ticket']}")
    print(f"     GA Fitness    : {result['ga_fitness']}")

    print(f"\n  ⚠️  Statistical Reality Check:")
    pr = result["phase3_reminder"]
    print(f"     Hot number test p-value : {pr['hot_number_p']}")
    print(f"     Overdue test p-value    : {pr['overdue_p']}")
    print(f"     Conclusion: {pr['conclusion']}")

print(f"\n{'='*60}")
print("✅ Phase 6 Complete")