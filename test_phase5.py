from app.services.genetic_algorithm import evolve
from app.services.monte_carlo import get_monte_carlo_report

print("\n🧬 Phase 5 — Genetic Algorithm\n")
print("=" * 60)

# Get Monte Carlo seeds first
mc       = get_monte_carlo_report("Lunchtime", n_sims=50_000)
seeds    = mc["candidate_tickets"]

print(f"Seeds from Monte Carlo: {len(seeds)} tickets")
print("\nEvolving population...\n")

result = evolve(draw_type="Lunchtime", seed_tickets=seeds, verbose=True)

print(f"\n{'='*60}")
print(f"🏆 Best Ticket Found  : {result['best_ticket']}")
print(f"   Fitness Score      : {result['best_fitness']}")
print(f"\n   Fitness Breakdown:")
for k, v in result["breakdown"].items():
    bar = "█" * int(v * 20)
    print(f"   {k:12s} : {bar:<20} {v:.4f}")

print(f"\n⚠️  {result['disclaimer']}")