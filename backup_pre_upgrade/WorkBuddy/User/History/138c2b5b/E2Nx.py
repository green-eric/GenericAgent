#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查缓存中的净资产数据"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa_scorer import Config

db_path = Config.QUARTERLY_DB_FILE
conn = sqlite3.connect(db_path)

# 查看缓存表结构
cursor = conn.execute("PRAGMA table_info(quarterly_cache)")
print("表结构:")
for row in cursor:
    print(f"  {row}")

# 查看方正证券的缓存
print("\n\n601901 方正证券 缓存:")
cursor = conn.execute("SELECT * FROM quarterly_cache WHERE ts_code LIKE ?", ("%601901%",))
for row in cursor:
    print(f"  {row}")

# 查看电投水电的缓存
print("\n600292 电投水电 缓存:")
cursor = conn.execute("SELECT * FROM quarterly_cache WHERE ts_code LIKE ?", ("%600292%",))
for row in cursor:
    print(f"  {row}")

# 查看新大陆的缓存
print("\n000997 新大陆 缓存:")
cursor = conn.execute("SELECT * FROM quarterly_cache WHERE ts_code LIKE ?", ("%000997%",))
for row in cursor:
    print(f"  {row}")

conn.close()
