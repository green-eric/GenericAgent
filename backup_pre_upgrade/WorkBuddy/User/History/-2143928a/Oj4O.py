import sqlite3
conn = sqlite3.connect(r'D:\Project\AnnualScorer\stock_cache.db')
# Check all tables and their schemas
cur = conn.execute('SELECT name, sql FROM sqlite_master WHERE type="table"')
for row in cur.fetchall():
    print(f"=== {row[0]} ===")
    print(row[1])
    print()
# Check financial_reports sample
cur = conn.execute('SELECT * FROM financial_reports WHERE ts_code="600338.SH" ORDER BY report_date DESC LIMIT 3')
for row in cur.fetchall():
    print(row)
conn.close()
