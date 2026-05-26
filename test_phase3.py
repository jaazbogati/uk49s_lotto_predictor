from app.services.stats_engine import (
    test_randomness,
    test_hot_number_predictive_power,
    test_overdue_predictive_power,
    test_draw_independence
)

print("\n🔬 Phase 3 — Statistical Tests\n")
print("=" * 60)

print("\n[1] Chi-Square Randomness Test — Lunchtime")
r = test_randomness("Lunchtime")
print(f"    Chi2     : {r['chi2']}")
print(f"    P-value  : {r['p_value']}")
print(f"    Verdict  : {r['conclusion']}")

print("\n[2] Chi-Square Randomness Test — Teatime")
r2 = test_randomness("Teatime")
print(f"    Chi2     : {r2['chi2']}")
print(f"    P-value  : {r2['p_value']}")
print(f"    Verdict  : {r2['conclusion']}")

print("\n[3] Hot Number Predictive Power — Lunchtime")
print("    (running... ~30 seconds)")
h = test_hot_number_predictive_power("Lunchtime")
print(f"    Random expected hits : {h['random_expected_hits']}")
print(f"    Actual average hits  : {h['actual_avg_hits']}")
print(f"    P-value              : {h['p_value']}")
print(f"    Verdict              : {h['conclusion']}")

print("\n[4] Overdue Score Predictive Power — Lunchtime")
print("    (running... ~60 seconds)")
o = test_overdue_predictive_power("Lunchtime")
print(f"    Avg overdue when appeared : {o['avg_overdue_when_appeared']}")
print(f"    Avg overdue when didn't   : {o['avg_overdue_when_didnt']}")
print(f"    P-value                   : {o['p_value']}")
print(f"    Verdict                   : {o['conclusion']}")

print("\n[5] Lunchtime vs Teatime Independence")
i = test_draw_independence()
print(f"    Avg shared numbers   : {i['avg_shared_numbers']}")
print(f"    Expected if random   : {i['expected_if_random']}")
print(f"    P-value              : {i['p_value']}")
print(f"    Verdict              : {i['conclusion']}")

print("\n" + "=" * 60)
print("✅ Phase 3 Complete")