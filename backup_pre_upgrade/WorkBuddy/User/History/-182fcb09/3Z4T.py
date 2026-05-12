#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

def check_database():
    conn = sqlite3.connect('stock_cache.db')
    cur = conn.execute('SELECT COUNT(*) FROM financial_reports WHERE report_type="annual" AND fetch_success=1')
    count = cur.fetchone()[0]
    print(f'年报数据条数: {count}')

    if count > 0:
        cur = conn.execute('SELECT ts_code, roe, gross_margin, net_margin, revenue_yoy, profit_yoy FROM financial_reports WHERE report_type="annual" AND fetch_success=1 LIMIT 5')
        rows = cur.fetchall()
        print('\n前5条年报数据:')
        for row in rows:
            print(f'{row[0]} {row[1]}: ROE={row[2]}, 毛利率={row[3]}, 净利率={row[4]}, 营收同比={row[5]}, 利润同比={row[6]}')
    else:
        print('没有找到有效的年报数据')

    conn.close()

if __name__ == "__main__":
    check_database()