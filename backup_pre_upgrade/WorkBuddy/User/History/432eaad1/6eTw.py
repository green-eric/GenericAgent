#!/usr/bin/env python3

import sqlite3
import pandas as pd

def check_no_fallback():
    print("=" * 80)
    print("A股智能选股系统 V7.0.0 - 移除兜底逻辑验证")
    print("验证时间: 2026-04-26 23:45")
    print("=" * 80)

    # 1. 读取新生成的Excel文件
    excel_path = "d:/Project/QAScorer/综合评分_20260426_234451.xlsx"
    df = pd.read_excel(excel_path, sheet_name="综合评价结果")

    # 2. 从数据库检查TTM数据
    db_path = "d:/Project/QAScorer/quarterly_cache.db"
    conn = sqlite3.connect(db_path)

    cursor = conn.cursor()
    rows = cursor.execute("""
        SELECT ts_code, roe_ttm, net_profit_ttm, net_assets_ttm
        FROM quarterly_ttm_cache
        ORDER BY ts_code
    """).fetchall()

    print("\nROE数据对比 (移除兜底逻辑后):")
    print("-" * 80)

    no_roe_count = 0
    fallback_used = 0

    for row in rows:
        ts_code, roe_ttm, net_profit, net_assets = row
        excel_row = df[df['股票代码'] == ts_code].iloc[0]

        if roe_ttm is None:
            no_roe_count += 1
            print(f"{ts_code}: TTM ROE为空 X (无ROE数据)")
        else:
            excel_roe = excel_row.iloc[3]
            if abs(float(roe_ttm) - float(excel_roe)) < 0.01:
                print(f"{ts_code}: TTM ROE={roe_ttm} OK")
            else:
                print(f"{ts_code}: TTM ROE={roe_ttm}, Excel={excel_roe} WARN")

    conn.close()

    # 3. 统计报告
    print("\n" + "=" * 80)
    print("移除兜底逻辑效果统计:")
    print("-" * 80)

    total_stocks = len(rows)
    roe_with_data = total_stocks - no_roe_count

    print(f"总股票数: {total_stocks}")
    print(f"有TTM ROE数据的股票: {roe_with_data}")
    print(f"无TTM ROE数据的股票: {no_roe_count}")
    print(f"ROE数据完整度: {roe_with_data/total_stocks*100:.1f}%")

    # 4. 影响分析
    print("\n" + "=" * 80)
    print("影响分析:")
    print("-" * 80)

    if no_roe_count > 0:
        print("WARNING: 以下股票将没有ROE数据:")
        for row in rows:
            ts_code, roe_ttm, _, _ = row
            if roe_ttm is None:
                excel_row = df[df['股票代码'] == ts_code].iloc[0]
                print(f"  - {ts_code} ({excel_row.iloc[1]})")
        print("\n这些股票的ROE字段将为空，可能影响评分。")
    else:
        print("SUCCESS: 所有股票都有TTM ROE数据，系统运行正常。")

    # 5. 总结
    print("\n" + "=" * 80)
    print("验证总结:")
    print("-" * 80)

    if no_roe_count == 0:
        status = "PASS - 所有股票都有ROE数据"
    elif no_roe_count <= 1:
        status = "WARN - 少量股票缺少ROE数据"
    else:
        status = "FAIL - 较多股票缺少ROE数据"

    print(f"系统状态: {status}")
    print(f"建议: {'可投入生产使用' if no_roe_count <= 1 else '需要处理缺失的ROE数据'}")

    print("\n" + "=" * 80)
    print("验证完成！")
    print("=" * 80)

if __name__ == "__main__":
    check_no_fallback()