#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

def check_database():
    conn = sqlite3.connect('stock_cache.db')
    cur = conn.execute('PRAGMA table_info(financial_reports)')
    columns = cur.fetchall()
    print('财务报表表结构:')
    for col in columns:
        print(f'  {col[1]} ({col[2]})')

    cur = conn.execute('SELECT COUNT(*) FROM financial_reports WHERE report_type="annual" AND fetch_success=1')
    count = cur.fetchone()[0]
    print(f'\n年报数据条数: {count}')

    if count > 0:
        cur = conn.execute('SELECT ts_code, roe, gross_margin, net_margin, revenue_yoy, profit_yoy FROM financial_reports WHERE report_type="annual" AND fetch_success=1 LIMIT 3')
        rows = cur.fetchall()
        print('\n前3条年报数据:')
        for row in rows:
            if len(row) >= 6:
                print(f'{row[0]}: ROE={row[1]}, 毛利率={row[2]}, 净利率={row[3]}, 营收同比={row[4]}, 利润同比={row[5]}')
            else:
                print(f'{row[0]}: 数据不完整')

    conn.close()

if __name__ == "__main__":
    check_database()