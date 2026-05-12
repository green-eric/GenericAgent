#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试缓存清除"""

import os, sys, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa_scorer import Config, _load_quarterly_from_db

# 查看601901的缓存
print("清除前:")
cached = _load_quarterly_from_db("601901")
print(f"  cached = {cached}")

# 尝试用不同格式清除
db_path = Config.QUARTERLY_DB_FILE
conn = sqlite3.connect(db_path)

# 查看ts_code格式
cursor = conn.execute("SELECT DISTINCT ts_code FROM quarterly_ttm_cache LIMIT 5")
print(f"\n缓存中ts_code格式:")
for row in cursor:
    print(f"  '{row[0]}'")

# 清除
conn.execute("DELETE FROM quarterly_ttm_cache WHERE ts_code LIKE ?", ("%601901%",))
conn.commit()

print("\n清除后:")
cached2 = _load_quarterly_from_db("601901")
print(f"  cached = {cached2}")

conn.close()
