import sqlite3
conn = sqlite3.connect(r'D:\Project\AnnualScorer\stock_cache.db')
# Check table schema
cur = conn.execute('PRAGMA table_info(financial_reports)')
print("financial_reports columns:")
for row in cur.fetchall():
    print(f"  {row[1]} ({row[2]})")
print()
# Check if there's a net_assets or equity field
cur = conn.execute('SELECT * FROM financial_reports WHERE ts_code="600338.SH" AND report_type="annual" ORDER BY report_date DESC LIMIT 1')
row = cur.fetchone()
print("Sample row (600338.SH):", row)
conn.close()
