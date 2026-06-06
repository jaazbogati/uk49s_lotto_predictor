from app.services.pattern_engine import get_top_pairs, check_pair_hits

print("Testing pair engine...")

pairs = get_top_pairs("Lunchtime", n=20)
print(f"✅ Top 20 pairs generated: {len(pairs)} pairs")
print(f"   Top pair: {pairs[0]['pair']} (count: {pairs[0]['count']})")

test_actual = [3, 12, 23, 34, 41, 47]
result      = check_pair_hits(pairs, test_actual)
print(f"   Hit count:    {result['hit_count']}")
print(f"   Hit rate:     {result['hit_rate']}%")
print(f"   Near misses:  {result['near_miss_count']}")
print(f"   Random base:  {result['random_baseline']}")