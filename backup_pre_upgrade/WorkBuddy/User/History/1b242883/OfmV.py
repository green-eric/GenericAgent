import sqlite3

conn = sqlite3.connect('quarterly_cache.db')

# Check if net assets data is available for ROE calculation
cur = conn.execute(
    "SELECT ts_code, net_assets_ttm FROM quarterly_ttm_cache WHERE ts_code='002466.SZ'"
)
row = cur.fetchone()
print(f'Net assets for ROE calc: {row[1]}')

# Check latest quarter net assets
cur = conn.execute('''
    SELECT pr.net_assets, qtc.net_assets_ttm
    FROM quarterly_reports pr
    JOIN (SELECT ts_code, MAX(report_date) as max_date FROM quarterly_reports GROUP BY ts_code) latest
    ON pr.ts_code=latest.ts_code AND pr.report_date=latest.max_date
    LEFT JOIN quarterly_ttm_cache qtc ON pr.ts_code=qtc.ts_code
    WHERE pr.ts_code='002466.SZ'
''')
row2 = cur.fetchone()
if row2:
    print(f'Latest quarter net assets: {row2[0]}')
    print(f'TTM net assets: {row2[1]}')

conn.close()