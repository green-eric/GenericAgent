#!/usr/bin/env python3

import sqlite3
import pandas as pd

def verify_ttm_roe():
    # 1. 从数据库检查TTM数据
    db_path = "d:/Project/QAScorer/quarterly_cache.db"
    conn = sqlite3.connect(db_path)

    print("=== 数据库中的TTM ROE数据 ===")
    cursor = conn.cursor()
    rows = cursor.execute("""
        SELECT ts_code, roe_ttm, net_profit_ttm, net_assets_ttm,
               revenue_yoy_latest, profit_yoy_latest, debt_ratio_latest
        FROM quarterly_ttm_cache
        ORDER BY roe_ttm DESC NULLS LAST
    """).fetchall()

    print(f"{'股票代码':<12} {'ROE_TTM(%)':<10} {'净利润_TTM(万)':<15} {'净资产(万)':<12} {'营收同比(%)':<12} {'净利润同比(%)':<12} {'资产负债率(%)':<12}")
    print("-" * 100)

    for row in rows:
        ts_code, roe_ttm, net_profit_ttm, net_assets_ttm, rev_yoy, prof_yoy, debt_ratio = row
        net_profit_wan = round(net_profit_ttm / 10000) if net_profit_ttm else None
        net_assets_wan = round(net_assets_ttm / 10000) if net_assets_ttm else None

        print(f"{ts_code:<12} {str(roe_ttm):<10} {str(net_profit_wan):<15} {str(net_assets_wan):<12} "
              f"{str(rev_yoy):<12} {str(prof_yoy):<12} {str(debt_ratio):<12}")

    conn.close()

    # 2. 检查Excel文件
    excel_path = "d:/Project/QAScorer/综合评分_20260426_233842.xlsx"
    try:
        df = pd.read_excel(excel_path, sheet_name="综合评价结果")

        print("\n=== Excel文件中的ROE数据（按总分排序）===")
        print(f"{'排名':<6} {'股票代码':<12} {'股票名称':<10} {'ROE(%)':<10} {'毛利率(%)':<10} {'净利率(%)':<10} {'营收同比(%)':<12} {'净利润同比(%)':<12}")
        print("-" * 90)

        for idx, row in df.iterrows():
            rank = idx + 1
            roe = row.iloc[3] if len(row) > 3 else None
            gross_margin = row.iloc[4] if len(row) > 4 else None
            net_margin = row.iloc[5] if len(row) > 5 else None
            rev_yoy = row.iloc[6] if len(row) > 6 else None
            prof_yoy = row.iloc[7] if len(row) > 7 else None

            print(f"{rank:<6} {row['股票代码']:<12} {row['股票名称']:<10} "
                  f"{str(roe):<10} {str(gross_margin):<10} {str(net_margin):<10} "
                  f"{str(rev_yoy):<12} {str(prof_yoy):<12}")

        # 统计信息
        roe_not_none = df.iloc[:, 3].notna().sum()  # ROE列是第4列（索引3）
        total_stocks = len(df)
        print(f"\n统计: TTM ROE有数据的股票 {roe_not_none}/{total_stocks} ({roe_not_none/total_stocks*100:.1f}%)")

    except Exception as e:
        print(f"读取Excel文件失败: {e}")

if __name__ == "__main__":
    verify_ttm_roe()