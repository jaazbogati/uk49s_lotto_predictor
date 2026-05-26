from app.services.bayesian_engine import get_bayesian_report
from app.services.monte_carlo import get_monte_carlo_report

print("\n🔵 Phase 4a — Bayesian Engine\n")
print("=" * 60)

report = get_bayesian_report("Lunchtime")
print(f"Draw type    : {report['label']}")
print(f"Total draws  : {report['total_draws']}")
print(f"Prob spread  : {report['prob_spread']}")
print(f"\nTop 10 by posterior probability (all-time):")
for r in report["top_10_alltime"]:
    print(f"  Number {r['number']:2d} → P = {r['posterior_prob']}")

print(f"\nTop 10 by recent posterior (last 90 days):")
for r in report["top_10_recent"]:
    print(f"  Number {r['number']:2d} → P = {r['recent_posterior']}")

print("\n")
print("=" * 60)
print("\n🎲 Phase 4b — Monte Carlo Engine\n")
print("=" * 60)

mc = get_monte_carlo_report("Lunchtime", n_sims=100_000)
print(f"Simulations run    : {mc['simulations']:,}")
print(f"Avg deviation      : {mc['avg_pct_deviation']}%")
print(f"Interpretation     : {mc['interpretation']}")
print(f"\nTop 10 by simulated frequency:")
for r in mc["top_10_simulated"][:5]:
    print(f"  Number {r['number']:2d} → {r['count']} hits ({r['pct_diff']:+.2f}% vs expected)")

print(f"\n🎟️  10 Candidate Tickets:")
for i, ticket in enumerate(mc["candidate_tickets"], 1):
    print(f"  Ticket {i:2d}: {ticket}")