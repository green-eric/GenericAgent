"""Debug: print detailed scores for stocks with data"""
import sys
import os
sys.path.insert(0, r'd:\Project\QAScorer')

import qa_scorer as qs
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

qs.setup_logging()
token = qs.load_token()
stocks = qs.load_stock_list()
print(f"Loaded {len(stocks)} stocks")

qs.init_db()

# Fetch data
raw_results, skipped = qs.fetch_batch_parallel(stocks, token, force_refresh=True)

# Print details for successful ones
print(f"\nSuccessful fetches: {sum(1 for r in raw_results if r.get('fetch_success'))}")
for r in raw_results:
    if r.get('fetch_success'):
        print(f"\n{r['ts_code']} {r['name']}:")
        print(f"  Annual: {r.get('metrics_annual', {})}")
        print(f"  Quarterly: {r.get('metrics_quarterly', {})}")
        print(f"  Annual date: {r.get('report_date_annual')}")
        print(f"  Quarterly date: {r.get('report_date_quarterly')}")
