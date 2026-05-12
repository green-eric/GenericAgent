#!/usr/bin/env python3

import sqlite3

def simple_field_check():
    print("=" * 80)
    print("A股智能选股系统 V7.0.0 - 字段验证报告")
    print("验证时间: 2026-04-26 23:40")
    print("=" * 80)

    # 从数据库获取详细TTM数据
    db_path = "d:/Project/QAScorer/quarterly_cache.db"
    conn = sqlite3.connect(db_path)

    cursor = conn.cursor()
    rows = cursor.execute("""
        SELECT
            ts_code,
            roe_ttm, net_profit_ttm, ocf_abs_ttm, net_assets_ttm,
            gross_margin_ttm, net_margin_ttm, ocf_ratio_ttm,
            revenue_yoy_latest, profit_yoy_latest, debt_ratio_latest,
            quarter_count, latest_quarter
        FROM quarterly_ttm_cache
        ORDER BY ts_code
    """).fetchall()

    # 统计各字段的数据情况
    field_stats = {
        "ROE_TTM": 0,
        "净利润_TTM": 0,
        "经营现金流_TTM": 0,
        "毛利率_TTM": 0,
        "净利率_TTM": 0,
        "OCF/净利润_TTM": 0,
        "营收同比(单季)": 0,
        "净利润同比(单季)": 0,
        "资产负债率(单季)": 0
    }

    print("\n各字段数据完整性检查:")
    print("-" * 80)

    for row in rows:
        ts_code = row[0]

        # 检查各字段
        if row[1] is not None: field_stats["ROE_TTM"] += 1
        if row[2] is not None: field_stats["净利润_TTM"] += 1
        if row[3] is not None: field_stats["经营现金流_TTM"] += 1
        if row[5] is not None: field_stats["毛利率_TTM"] += 1
        if row[6] is not None: field_stats["净利率_TTM"] += 1
        if row[8] is not None: field_stats["OCF/净利润_TTM"] += 1
        if row[9] is not None: field_stats["营收同比(单季)"] += 1
        if row[10] is not None: field_stats["净利润同比(单季)"] += 1
        if row[11] is not None: field_stats["资产负债率(单季)"] += 1

        # 显示前5只股票的详细信息
        if len(field_stats) <= 5:
            print(f"\n{ts_code}:")
            print(f"  ROE_TTM: {row[1]}")
            print(f"  净利润_TTM: {row[2]}")
            print(f"  经营现金流_TTM: {row[3]}")
            print(f"  毛利率_TTM: {row[5]}")
            print(f"  净利率_TTM: {row[6]}")

    conn.close()

    # 统计报告
    print("\n" + "=" * 80)
    print("字段数据完整性统计:")
    print("-" * 80)

    total_stocks = len(rows)
    for field_name, count in field_stats.items():
        percentage = count / total_stocks * 100
        status = "✅" if percentage >= 90 else "⚠️" if percentage >= 70 else "❌"
        print(f"{field_name:20}: {count}/{total_stocks} ({percentage:.1f}%) {status}")

    # TTM计算验证
    print("\n" + "=" * 80)
    print("TTM计算逻辑验证:")
    print("-" * 80)

    cursor = sqlite3.connect(db_path).cursor()

    # 验证ROE_TTM计算
    ttm_roe_success = cursor.execute("SELECT COUNT(*) FROM quarterly_ttm_cache WHERE roe_ttm IS NOT NULL").fetchone()[0]
    ttm_roe_total = cursor.execute("SELECT COUNT(*) FROM quarterly_ttm_cache").fetchone()[0]

    print(f"TTM ROE计算成功率: {ttm_roe_success}/{ttm_roe_total} ({ttm_roe_success/ttm_roe_total*100:.1f}%)")

    # 示例验证
    sample_rows = cursor.execute("""
        SELECT ts_code, net_profit_ttm, net_assets_ttm, roe_ttm
        FROM quarterly_ttm_cache
        WHERE roe_ttm IS NOT NULL AND net_profit_ttm IS NOT NULL AND net_assets_ttm IS NOT NULL
        LIMIT 3
    """).fetchall()

    print("\nTTM ROE计算示例验证:")
    for ts_code, net_profit, net_assets, roe in sample_rows:
        if net_assets and net_assets > 0:
            calculated_roe = round(net_profit / net_assets * 100, 2)
            match = "✅" if abs(calculated_roe - roe) < 0.01 else "❌"
            print(f"  {ts_code}: 净利润={net_profit}, 净资产={net_assets}")
            print(f"         计算ROE={calculated_roe}%, 实际ROE={roe}% {match}")

    cursor.close()

    # 数据源分析
    print("\n" + "=" * 80)
    print("数据源分布分析:")
    print("-" * 80)

    cursor = sqlite3.connect(db_path).cursor()
    annual_fallback = cursor.execute("""
        SELECT COUNT(*)
        FROM quarterly_ttm_cache q
        LEFT JOIN (SELECT DISTINCT ts_code, roe AS annual_roe FROM quarterly_reports WHERE roe IS NOT NULL) r
        ON q.ts_code = r.ts_code
        WHERE q.roe_ttm IS NULL AND r.annual_roe IS NOT NULL
    """).fetchone()[0]

    print(f"使用年报ROE兜底的数量: {annual_fallback}/{ttm_roe_total}")

    cursor.close()

    print("\n" + "=" * 80)
    print("验证完成！")
    print("=" * 80)

if __name__ == "__main__":
    simple_field_check()