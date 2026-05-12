#!/usr/bin/env python3
import sqlite3

# 连接数据库
conn = sqlite3.connect('quarterly_cache.db')
cursor = conn.cursor()

try:
    # 查看所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("数据库表名:")
    for table in tables:
        print(f"  {table[0]}")

    if tables:
        # 查看第一个表的字段信息
        table_name = tables[0][0]
        print(f"\n{table_name}表结构:")
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col}")

        # 查看数据样本
        print(f"\n{table_name}数据样例:")
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
        rows = cursor.fetchall()
        for row in rows:
            print(f"  {row}")

except Exception as e:
    print(f"错误: {e}")
finally:
    conn.close()