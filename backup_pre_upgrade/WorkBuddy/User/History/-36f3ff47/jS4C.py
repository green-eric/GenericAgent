#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

def check_annual_db():
    conn = sqlite3.connect('年报/stock_cache.db')
    cur = conn.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables = cur.fetchall()
    print('数据库表:', [t[0] for t in tables])

    if 'financial_reports' in [t[0] for t in tables]:
        cur = conn.execute('SELECT COUNT(*) FROM financial_reports WHERE report_type="annual"')
        count = cur.fetchone()[0]
        print(f'财务报表数据: {count} 条')
    else:
        print('financial_reports 表不存在')

    conn.close()

if __name__ == "__main__":
    check_annual_db()