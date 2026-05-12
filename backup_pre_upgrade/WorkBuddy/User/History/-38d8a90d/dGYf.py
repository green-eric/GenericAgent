#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
展示使用真实股票列表的A股智能选股分析系统报告
"""

import pandas as pd

def show_real_list_report():
    """展示真实列表分析结果"""
    try:
        # 读取主结果表
        df_main = pd.read_excel('C:\\Users\\green\\Desktop\\股票业绩评价_20260424_2051_真实列表.xlsx', sheet_name='综合评价结果')

        print("=== A股智能选股分析报告（真实股票列表版） ===")
        print(f"生成时间: 2026年4月24日 20:51")
        print(f"分析股票总数: {len(df_main)}")

        # 评级分布
        rating_counts = df_main['评级'].value_counts().sort_index()
        print(f"\n=== 评级分布 ===")
        for rating, count in rating_counts.items():
            percentage = count / len(df_main) * 100
            print(f"{rating}级: {count}只 ({percentage:.1f}%)")

        # 统计概览
        df_stats = pd.read_excel('C:\\Users\\green\\Desktop\\股票业绩评价_20260424_2051_真实列表.xlsx', sheet_name='统计概览')
        print(f"\n=== 统计概览 ===")
        print(df_stats.to_string(index=False))

        # 绩优股(A级)
        try:
            df_a = pd.read_excel('C:\\Users\\green\\Desktop\\股票业绩评价_20260424_2051_真实列表.xlsx', sheet_name='绩优股(A级)')
            if not df_a.empty:
                print(f"\n=== A级绩优股 (前5只) ===")
                display_cols = ['股票代码', '股票名称', '行业', '总评分', 'TTM扣非ROE(%)', '营收同比增速(%)']
                print(df_a[display_cols].head().to_string(index=False))
            else:
                print(f"\n=== A级绩优股 ===")
                print("暂无A级股票")
        except:
            print(f"\n=== A级绩优股 ===")
            print("暂无A级股票")

        # 最高评分股票
        if len(df_main) > 0:
            max_score_stock = df_main.loc[df_main['总评分'].idxmax()]
            print(f"\n=== 最高评分股票 ===")
            print(f"股票: {max_score_stock['股票名称']}({max_score_stock['股票代码']})")
            print(f"评分: {max_score_stock['总评分']:.1f}")
            print(f"行业: {max_score_stock['行业']}")
            print(f"TTM扣非ROE: {max_score_stock['TTM扣非ROE(%)']}%")
            print(f"营收增速: {max_score_stock['营收同比增速(%)']}%")

        # 详细展示部分股票
        print(f"\n=== 部分股票详细指标 ===")
        sample_stocks = df_main.head(10)
        display_cols = ['股票代码', '股票名称', '评级', '总评分', 'TTM扣非ROE(%)', '毛利率(%)', '营收同比增速(%)']
        print(sample_stocks[display_cols].to_string(index=False))

        print(f"\n=== 报告总结 ===")
        print("本系统基于真实股票列表进行A股智能选股分析:")
        print("- 股票来源: C:\\Users\\green\\Desktop\\gy\\xuan.txt")
        print("- 分析数量: 50只股票（测试样本）")
        print("- 分析方法: 五维度评价体系")
        print("- 输出结果: Excel专业分析报告")
        print("\n该系统可为投资者提供科学的股票筛选和投资决策支持。")

    except Exception as e:
        print(f"读取报告失败: {e}")

if __name__ == "__main__":
    show_real_list_report()