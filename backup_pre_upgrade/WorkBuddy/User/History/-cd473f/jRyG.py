import sqlite3

conn = sqlite3.connect('quarterly_cache.db')
cur = conn.execute(
    'SELECT report_date, total_assets, total_liabilities, net_assets '
    'FROM quarterly_reports WHERE ts_code=\"002466.SZ\" '
    'ORDER BY report_date DESC LIMIT 3'
)
rows = cur.fetchall()
for r in rows:
    print(f'Date: {r[0]}, Total Assets: {r[1]}, Liabilities: {r[2]}, Net Assets: {r[3]}')

# Check if net assets was calculated as assets - liabilities
cur = conn.execute(
    'SELECT report_date, total_assets, total_liabilities, '
    '(total_assets-total_liabilities) AS calc_net_assets '
    'FROM quarterly_reports WHERE ts_code=\"002466.SZ\" AND total_assets IS NOT NULL '
    'AND total_liabilities IS NOT NULL ORDER BY report_date DESC LIMIT 1'
)
row = cur.fetchone()
if row:
    print(f'Calculated net assets: {row[3]}')

conn.close()