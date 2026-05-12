#!/usr/bin/env python3

import sqlite3

def check_roe_data():
    # 检查季报数据库
    quarterly_db = "d:/Project/QAScorer/quarterly_cache.db"
    conn = sqlite3.connect(quarterly_db)

    print("=== 002466.SZ (天齐锂业) 的TTM数据 ===")
    cursor = conn.cursor()
    row = cursor.execute("""
        SELECT ts_code, roe_ttm, net_profit_ttm, net_assets_ttm,
               revenue_yoy_latest, profit_yoy_latest, debt_ratio_latest
        FROM quarterly_ttm_cache WHERE ts_code = '002466.SZ'
    """).fetchone()

    if row:
        ts_code, roe_ttm, net_profit_ttm, net_assets_ttm, rev_yoy, prof_yoy, debt_ratio = row
        print(f"股票代码: {ts_code}")
        print(f"ROE_TTM: {roe_ttm}")
        print(f"净利润_TTM: {net_profit_ttm}")
        print(f"净资产_TTM: {net_assets_ttm}")
        print(f"营收同比: {rev_yoy}")
        print(f"净利润同比: {prof_yoy}")
        print(f"资产负债率: {debt_ratio}")

    # 检查年报数据库
    annual_db = "d:/Project/QAScorer/../AnnualScorer/stock_cache.db"
    try:
        conn2 = sqlite3.connect(annual_db)
        cursor2 = conn2.cursor()

        print("\n=== 年报数据库中的002466.SZ数据 ===")
        report_row = cursor2.execute("""
            SELECT report_date, roe, net_profit, ocf_abs
            FROM financial_reports
            WHERE ts_code='002466.SZ' AND report_type='annual' AND fetch_success=1
            ORDER BY report_date DESC LIMIT 1
        """).fetchone()

        if report_row:
            report_date, roe_annual, net_profit_annual, ocf_abs_annual = report_row
            print(f"年报日期: {report_date}")
            print(f"年报ROE: {roe_annual}")
            print(f"年报净利润: {net_profit_annual}")
            print(f"年报经营现金流: {ocf_abs_annual}")

        conn2.close()
    except Exception as e:
        print(f"访问年报数据库失败: {e}")

    conn.close()

if __name__ == "__main__":
    check_roe_data()