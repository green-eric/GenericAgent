"""
使用之前验证过的 API 返回数据分析季度字段
直接从缓存数据库读取已保存的 API 响应
"""
import sqlite3, json, re, os

db_path = r'c:\Users\green\WorkBuddy\20260424203734\workplace\stock_cache.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 查看数据库中有哪些表
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print(f"数据库表: {tables}")

# 查看 financial_reports 表的记录
cur.execute("SELECT ts_code, report_date, report_type, fetch_success FROM financial_reports LIMIT 20")
rows = cur.fetchall()
print(f"\nfinancial_reports 前20条:")
for r in rows:
    print(f"  {r}")

# 统计
cur.execute("SELECT report_type, COUNT(*) FROM financial_reports GROUP BY report_type")
type_counts = cur.fetchall()
print(f"\n按类型统计: {type_counts}")

cur.execute("SELECT COUNT(DISTINCT ts_code) FROM financial_reports WHERE fetch_success=1")
success_count = cur.fetchone()[0]
print(f"有成功记录的股票数: {success_count}")

conn.close()
