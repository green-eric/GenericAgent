#!/usr/bin/env python3

import sqlite3
import pandas as pd

def comprehensive_verification():
    print("=" * 80)
    print("A股智能选股系统 V7.0.0 - 全字段验证报告")
    print("验证时间: 2026-04-26 23:40")
    print("=" * 80)

    # 1. 从数据库获取详细TTM数据
    db_path = "d:/Project/QAScorer/quarterly_cache.db"
    conn = sqlite3.connect(db_path)

    cursor = conn.cursor()
    rows = cursor.execute("""
        SELECT
            ts_code,
            roe_ttm, net_profit_ttm, ocf_abs_ttm, net_assets_ttm,
            gross_margin_ttm, net_margin_ttm, ocf_ratio_ttm,
            revenue_yoy_latest, profit_yoy_latest, debt_ratio_latest,
            total_assets_latest, total_liabilities_latest,
            quarter_count, latest_quarter
        FROM quarterly_ttm_cache
        ORDER BY ts_code
    """).fetchall()

    # 2. 读取Excel文件进行对比
    excel_path = "d:/Project/QAScorer/综合评分_20260426_233842.xlsx"
    df = pd.read_excel(excel_path, sheet_name="综合评价结果")

    print("\n📊 字段验证结果汇总:")
    print("-" * 80)

    verification_results = {
        "ROE_TTM": {"total": 0, "success": 0, "failed": 0},
        "净利润_TTM": {"total": 0, "success": 0, "failed": 0},
        "经营现金流_TTM": {"total": 0, "success": 0, "failed": 0},
        "毛利率_TTM": {"total": 0, "success": 0, "failed": 0},
        "净利率_TTM": {"total": 0, "success": 0, "failed": 0},
        "OCF/净利润_TTM": {"total": 0, "success": 0, "failed": 0},
        "营收同比(单季)": {"total": 0, "success": 0, "failed": 0},
        "净利润同比(单季)": {"total": 0, "success": 0, "failed": 0},
        "资产负债率(单季)": {"total": 0, "success": 0, "failed": 0}
    }

    for i, row in enumerate(rows):
        ts_code = row[0]

        # 查找对应的Excel行
        excel_row = df[df['股票代码'] == ts_code].iloc[0] if not df[df['股票代码'] == ts_code].empty else None

        print(f"\n🔍 {ts_code} ({excel_row.iloc[1] if excel_row is not None else 'N/A'}):")

        fields_to_check = [
            ("ROE_TTM", row[1], excel_row.iloc[3] if excel_row is not None and len(excel_row) > 3 else None, "ttm_metrics"),
            ("净利润_TTM", row[2], excel_row.iloc[10] if excel_row is not None and len(excel_row) > 10 else None, "ttm_metrics"),
            ("经营现金流_TTM", row[3], excel_row.iloc[11] if excel_row is not None and len(excel_row) > 11 else None, "ttm_metrics"),
            ("毛利率_TTM", row[5], excel_row.iloc[4] if excel_row is not None and len(excel_row) > 4 else None, "ttm_metrics"),
            ("净利率_TTM", row[6], excel_row.iloc[5] if excel_row is not None and len(excel_row) > 5 else None, "ttm_metrics"),
            ("OCF/净利润_TTM", row[8], None, "ttm_metrics"),  # OCF/净利润在Excel中没有直接显示
            ("营收同比(单季)", row[9], excel_row.iloc[6] if excel_row is not None and len(excel_row) > 6 else None, "latest_quarterly"),
            ("净利润同比(单季)", row[10], excel_row.iloc[7] if excel_row is not None and len(excel_row) > 7 else None, "latest_quarterly"),
            ("资产负债率(单季)", row[11], excel_row.iloc[8] if excel_row is not None and len(excel_row) > 8 else None, "latest_quarterly")
        ]

        for field_name, db_value, excel_value, source_type in fields_to_check:
            verification_results[field_name]["total"] += 1

            if db_value is None:
                status = "❌ 数据库为空"
                verification_results[field_name]["failed"] += 1
            elif excel_value is None:
                status = "⚠️ Excel中无数据"
                verification_results[field_name]["failed"] += 1
            elif abs(float(db_value or 0) - float(excel_value or 0)) < 0.01:  # 允许小数点后两位的误差
                status = "✅ 匹配"
                verification_results[field_name]["success"] += 1
            else:
                status = f"❌ 不匹配 (DB:{db_value}, Excel:{excel_value})"
                verification_results[field_name]["failed"] += 1

            print(f"   {field_name:15}: {status}")

    conn.close()

    # 3. 统计报告
    print("\n" + "=" * 80)
    print("📈 字段验证统计报告:")
    print("-" * 80)

    for field_name, results in verification_results.items():
        success_rate = results["success"] / results["total"] * 100 if results["total"] > 0 else 0
        print(f"{field_name:15}: {results['success']}/{results['total']} ({success_rate:.1f}%)")

    # 4. 数据源分析
    print("\n🎯 数据源分布分析:")
    print("-" * 80)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM quarterly_ttm_cache WHERE roe_ttm IS NOT NULL")
    ttm_roe_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM quarterly_ttm_cache")
    total_count = cursor.fetchone()[0]

    print(f"TTM ROE有数据: {ttm_roe_count}/{total_count} ({ttm_roe_count/total_count*100:.1f}%)")
    print(f"使用年报兜底: {total_count - ttm_roe_count}/{total_count} ({(total_count - ttm_roe_count)/total_count*100:.1f}%)")

    # 5. 详细异常分析
    print("\n⚠️ 异常情况详细分析:")
    print("-" * 80)

    failed_fields = []
    for field_name, results in verification_results.items():
        if results["failed"] > 0:
            failed_fields.append(field_name)

    if failed_fields:
        print("以下字段存在匹配问题:")
        for field in failed_fields:
            print(f"  - {field}: {verification_results[field]['failed']}个失败")
    else:
        print("🎉 所有字段验证通过，无匹配问题！")

    print("\n" + "=" * 80)
    print("✅ 验证完成！")
    print("=" * 80)

if __name__ == "__main__":
    comprehensive_verification()