#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa_scorer import Config

print(f"DB路径: {Config.QUARTERLY_DB_FILE}")
print(f"DB存在: {os.path.exists(Config.QUARTERLY_DB_FILE)}")

conn = sqlite3.connect(Config.QUARTERLY_DB_FILE)
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"表列表: {tables}")

for t in tables:
    table_name = t[0]
    print(f"\n{'='*60}")
    print(f"表: {table_name}")
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    for row in cursor:
        print(f"  {row}")
    
    # 查看行数
    cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"  行数: {count}")
    
    # 查看前3行
    cursor = conn.execute(f"SELECT * FROM {table_name} LIMIT 3")
    for row in cursor:
        print(f"  {row}")

conn.close()
