#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
比较AnnualScorer和QAScorer的A级股票交集
"""

import pandas as pd
import sys

def main():
    annual_file = 'D:/Project/AnnualScorer/股票业绩评价_20260426_204545.xlsx'
    quarterly_file = 'D:/Project/QAScorer/综合评分_20260427_004204.xlsx'

    print("=" * 80)
    print("AnnualScorer vs QAScorer A级股票比较分析")
    print("=" * 80)

    # 读取两个Excel文件
    try:
        annual_df = pd.read_excel(annual_file)
        print(f"✅ AnnualScorer文件加载成功: {len(annual_df)}只股票")
    except Exception as e:
        print(f"❌ 读取AnnualScorer文件失败: {e}")
        return

    try:
        quarterly_df = pd.read_excel(quarterly_file)
        print(f"✅ QAScorer文件加载成功: {len(quarterly_df)}只股票")
    except Exception as e:
        print(f"❌ 读取QAScorer文件失败: {e}")
        return

    # 检查必要的列
    if '评级' not in annual_df.columns:
        print("❌ AnnualScorer文件中缺少'评级'列")
        return

    if '总分' not in quarterly_df.columns:
        print("❌ QAScorer文件中缺少'总分'列")
        return

    # 查找A级股票
    annual_a_stocks = annual_df[annual_df['评级'] == 'A']
    print(f"\n📊 AnnualScorer A级股票数量: {len(annual_a_stocks)}")

    # QAScorer的高分股票 (80分以上)
    quarterly_high_score = quarterly_df[quarterly_df['总分'] >= 80]
    print(f"📊 QAScorer 80分以上股票数量: {len(quarterly_high_score)}")

    # 获取股票代码
    annual_a_codes = set(annual_a_stocks['股票代码'].tolist())
    quarterly_high_codes = set(quarterly_high_score['股票代码'].tolist())

    # 找出共同存在的股票
    common_stocks = annual_a_codes.intersection(quarterly_high_codes)
    print(f"\n🎯 同时存在的高分股票数量: {len(common_stocks)}")

    if len(common_stocks) > 0:
        print(f"\n📋 同时在两个系统中被评为高分的股票列表:")

        # 按股票代码排序显示前20只
        sorted_common = sorted(common_stocks)
        for i, code in enumerate(sorted_common[:20], 1):
            annual_row = annual_a_stocks[annual_a_stocks['股票代码'] == code].iloc[0]
            quarterly_row = quarterly_high_score[quarterly_high_score['股票代码'] == code].iloc[0]

            print(f"{i:2d}. {code} | AnnualScorer: {annual_row['股票名称']} ({annual_row['总分']:.1f}) | QAScorer: {quarterly_row['股票名称']} ({quarterly_row['总分']:.1f})")

        if len(sorted_common) > 20:
            print(f"\n... 还有 {len(sorted_common) - 20} 只股票未显示")

        print(f"\n共找到 {len(common_stocks)} 只同时在两个系统中被评为高分的股票")

        # 详细对比分析
        print(f"\n🔍 详细对比分析:")
        print(f"   AnnualScorer A级占比: {len(annual_a_stocks)/len(annual_df)*100:.1f}%")
        print(f"   QAScorer 高分占比: {len(quarterly_high_score)/len(quarterly_df)*100:.1f}%")
        print(f"   交集占比: {len(common_stocks)/len(annual_df)*100:.1f}%")

        # 保存详细结果
        with open('d:/Project/QAScorer/A级股票交集分析.txt', 'w', encoding='utf-8') as f:
            f.write("AnnualScorer vs QAScorer A级股票交集分析报告\n")
            f.write("=" * 50 + "\n")
            f.write(f"分析时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write(f"AnnualScorer A级股票数量: {len(annual_a_stocks)}\n")
            f.write(f"QAScorer 高分股票数量: {len(quarterly_high_score)}\n")
            f.write(f"同时存在的高分股票数量: {len(common_stocks)}\n\n")

            f.write("同时在两个系统中被评为高分的股票:\n")
            for i, code in enumerate(sorted_common, 1):
                annual_row = annual_a_stocks[annual_a_stocks['股票代码'] == code].iloc[0]
                quarterly_row = quarterly_high_score[quarterly_high_score['股票代码'] == code].iloc[0]

                f.write(f"{i:2d}. {code} | AnnualScorer: {annual_row['股票名称']} ({annual_row['总分']:.1f}) | QAScorer: {quarterly_row['股票名称']} ({quarterly_row['总分']:.1f})\n")

        print(f"\n📄 详细分析报告已保存到: d:/Project/QAScorer/A级股票交集分析.txt")

    else:
        print(f"\n❌ 未找到同时在两个系统中被评为高分的股票")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()