#!/usr/bin/env python3

import sqlite3

def check_database():
    db_path = "d:/Project/QAScorer/quarterly_cache.db"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查表
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        print('Tables:', [t[0] for t in tables])

        if 'quarterly_reports' in [t[0] for t in tables]:
            cursor.execute('PRAGMA table_info(quarterly_reports)')
            print('\nquarterly_reports schema:')
            for row in cursor.fetchall():
                print(row)

        if 'quarterly_ttm_cache' in [t[0] for t in tables]:
            cursor.execute('PRAGMA table_info(quarterly_ttm_cache)')
            print('\nquarterly_ttm_cache schema:')
            for row in cursor.fetchall():
                print(row)

        # 检查数据
        if 'quarterly_reports' in [t[0] for t in tables]:
            count = cursor.execute("SELECT COUNT(*) FROM quarterly_reports").fetchone()[0]
            print(f'\nquarterly_reports record count: {count}')

        if 'quarterly_ttm_cache' in [t[0] for t in tables]:
            count = cursor.execute("SELECT COUNT(*) FROM quarterly_ttm_cache").fetchone()[0]
            print(f'quarterly_ttm_cache record count: {count}')

            # 查看一些TTM数据
            rows = cursor.execute("SELECT ts_code, roe_ttm, net_profit_ttm FROM quarterly_ttm_cache LIMIT 5").fetchall()
            print('\nSample TTM data:')
            for row in rows:
                print(f"  {row[0]}: ROE_TTM={row[1]}, NetProfit_TTM={row[2]}")

        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_database()