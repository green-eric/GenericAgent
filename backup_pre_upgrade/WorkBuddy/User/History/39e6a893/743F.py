#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
展示A股智能选股分析系统生成的Excel报告
"""

import pandas as pd

def show_excel_report():
    """展示Excel报告内容"""
    try:
        # 读取主结果表
        df_main = pd.read_excel('C:\\Users\\green\\Desktop\\股票业绩评价_20260424_2048.xlsx', sheet_name='综合评价结果')

        print("=== A股智能选股分析报告 ===")
        print(f"生成时间: 2026年4月24日 20:48")
        print(f"分析股票总数: {len(df_main)}")

        # 评级分布
        rating_counts = df_main['评级'].value_counts().sort_index()
        print(f"\n=== 评级分布 ===")
        for rating, count in rating_counts.items():
            percentage = count / len(df_main) * 100
            print(f"{rating}级: {count}只 ({percentage:.1f}%)")

        # 统计概览
        df_stats = pd.read_excel('C:\\Users\\green\\Desktop\\股票业绩评价_20260424_2048.xlsx', sheet_name='统计概览')
        print(f"\n=== 统计概览 ===")
        print(df_stats.to_string(index=False))

        # 绩优股(A级)
        try:
            df_a = pd.read_excel('C:\\Users\\green\\Desktop\\股票业绩评价_20260424_2048.xlsx', sheet_name='绩优股(A级)')
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

        # 按行业统计
        print(f"\n=== 各行业平均评分 ===")
        industry_avg = df_main.groupby('行业')['总评分'].agg(['mean', 'count']).round(2)
        industry_avg.columns = ['平均评分', '股票数量']
        print(industry_avg.sort_values('平均评分', ascending=False).to_string())

        # 最高评分股票
        max_score_stock = df_main.loc[df_main['总评分'].idxmax()]
        print(f"\n=== 最高评分股票 ===")
        print(f"股票: {max_score_stock['股票名称']}({max_score_stock['股票代码']})")
        print(f"评分: {max_score_stock['总评分']:.1f}")
        print(f"行业: {max_score_stock['行业']}")
        print(f"TTM扣非ROE: {max_score_stock['TTM扣非ROE(%)']}%")
        print(f"营收增速: {max_score_stock['营收同比增速(%)']}%")

        print(f"\n=== 报告总结 ===")
        print("本系统基于五维度评价体系:")
        print("1. 盈利能力 - TTM扣非ROE、毛利率、净利率")
        print("2. 成长性 - 营收/利润同比、单季环比")
        print("3. 盈利质量 - 经营现金流/净利润、应收账款占比")
        print("4. 运营效率 - 总资产周转率、存货周转率")
        print("5. 偿债风险 - 资产负债率、利息保障倍数")
        print("\n采用行业百分位评分确保跨行业可比性")
        print("A~E分级反映综合业绩水平")

    except Exception as e:
        print(f"读取报告失败: {e}")

if __name__ == "__main__":
    show_excel_report()