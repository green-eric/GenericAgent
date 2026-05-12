import subprocess, json, sys

result = subprocess.run(["codexbar.exe", "cost", "-p", "all", "--json"], capture_output=True, text=True)
data = json.loads(result.stdout)

print("=" * 60)
print("  Token Cost Report (Last 30 Days)")
print("=" * 60)

total_usd = 0
for p in data:
    provider = p.get("provider", "?")
    supported = p.get("supported", False)
    cost = p.get("cost", {})
    tokens = p.get("tokens", {})
    sessions = p.get("sessions_count", 0)
    by_model = p.get("by_model", {})
    days = p.get("days_scanned", "?")
    period_start = (p.get("period") or {}).get("start")
    period_end = (p.get("period") or {}).get("end")
    
    if not supported or cost.get("total_usd", 0) == 0:
        continue
    
    total_usd += cost["total_usd"]
    
    print(f"\n--- {provider.upper()} ---")
    print(f"  Cost:     ${cost['total_usd']:.4f} {cost.get('currency','USD')}")
    print(f"  Tokens:   Input: {tokens.get('input', 0):,} | Output: {tokens.get('output', 0):,} | Cached: {tokens.get('cached', 0):,}")
    print(f"  Sessions: {sessions} | Scanned: {days} days")
    if period_start and period_end:
        print(f"  Period:   {period_start} ~ {period_end}")
    if by_model:
        for model, m_cost in by_model.items():
            short_name = model[:50] + ("..." if len(model) > 50 else "")
            print(f"    Model: {short_name}: ${m_cost:.4f}")

print(f"\n{'=' * 60}")
print(f"  TOTAL: ${total_usd:.4f}")
print(f"{'=' * 60}")

# Also show providers with errors
unsupported = [p for p in data if not p.get("supported")]
if unsupported:
    print(f"\n  ({len(unsupported)} providers do not support local cost scanning)")
