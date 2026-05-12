"""Debug run - add logging to fetch_batch parallel section"""
import sys
import os
sys.path.insert(0, r'd:\Project\QAScorer')

# Patch fetch_annual_and_quarterly to add debug output
import qa_scorer as qs

original_fetch = qs.fetch_annual_and_quarterly

def debug_fetch(ts_code, name, token, session):
    print(f"  [DEBUG] fetch_annual_and_quarterly called: {ts_code} {name}")
    result = original_fetch(ts_code, name, token, session)
    print(f"  [DEBUG] result: fetch_success={result.get('fetch_success')}, has_annual={bool(result.get('metrics_annual'))}, has_quarterly={bool(result.get('metrics_quarterly'))}")
    return result

qs.fetch_annual_and_quarterly = debug_fetch

# Now run main
qs.main()
