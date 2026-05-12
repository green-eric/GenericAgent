import sqlite3
conn = sqlite3.connect('stock_cache.db')
c = conn.execute("SELECT COUNT(*) FROM financial_reports WHERE report_type='annual' AND fetch_success=1")
print('已缓存年报记录:', c.fetchone()[0])
c2 = conn.execute("SELECT COUNT(DISTINCT ts_code) FROM financial_reports WHERE report_type='annual' AND fetch_success=1")
print('已缓存股票数:', c2.fetchone()[0])
c3 = conn.execute("SELECT COUNT(*) FROM stocks")
print('stocks表记录:', c3.fetchone()[0])
conn.close()
