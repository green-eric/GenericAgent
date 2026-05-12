#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
展示包含完整行业分类的真实数据版本A股智能选股分析报告
"""

import pandas as pd

def show_real_data_report():
    """展示真实数据版本的分析报告"""
    try:
        # 读取主结果表
        df_main = pd.read_excel('C:\\Users\\green\\Desktop\\A股智能选股分析报告_20260424_2056.xlsx', sheet_name='综合评价结果')

        print("=== A股智能选股分析报告（真实数据版） ===")
        print(f"生成时间: 2026年4月24日 20:56")
        print(f"分析股票总数: {len(df_main)}")

        # 评级分布
        rating_counts = df_main['评级'].value_counts().sort_index()
        print(f"\n=== 评级分布 ===")
        for rating, count in rating_counts.items():
            percentage = count / len(df_main) * 100
            print(f"{rating}级: {count}只 ({percentage:.1f}%)")

        # 行业分布
        industry_counts = df_main['行业'].value_counts()
        print(f"\n=== 行业分布 ===")
        for industry, count in industry_counts.items():
            percentage = count / len(df_main) * 100
            print(f"{industry}: {count}只 ({percentage:.1f}%)")

        # 统计概览
        df_stats = pd.read_excel('C:\\Users\\green\\Desktop\\A股智能选股分析报告_20260424_2056.xlsx', sheet_name='统计概览')
        print(f"\n=== 统计概览 ===")
        print(df_stats.to_string(index=False))

        # 行业分析
        try:
            df_industry = pd.read_excel('C:\\Users\\green\\Desktop\\A股智能选股分析报告_20260424_2056.xlsx', sheet_name='行业分析')
            print(f"\n=== 行业分析 ===")
            print(df_industry.to_string(index=True))
        except:
            print(f"\n=== 行业分析 ===")
            print("暂无详细行业分析数据")

        # 绩优股(A级)
        try:
            df_a = pd.read_excel('C:\\Users\\green\\Desktop\\A股智能选股分析报告_20260424_2056.xlsx', sheet_name='绩优股(A级)')
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
        display_cols = ['股票代码', '股票名称', '行业', '评级', '总评分', 'TTM扣非ROE(%)', '毛利率(%)', '营收同比增速(%)']
        print(sample_stocks[display_cols].to_string(index=False))

        # 行业表现对比
        print(f"\n=== 各行业平均表现 ===")
        industry_performance = df_main.groupby('行业').agg({
            '总评分': 'mean',
            'TTM扣非ROE(%)': 'mean',
            '营收同比增速(%)': 'mean',
            '股票代码': 'count'
        }).round(2)
        industry_performance.columns = ['平均评分', '平均ROE', '平均营收增速', '股票数量']
        print(industry_performance.sort_values('平均评分', ascending=False).to_string())

        print(f"\n=== 系统功能总结 ===")
        print("✅ 完整行业分类对接 - 基于真实行业特征映射")
        print("✅ TTM财务指标计算 - 滚动十二个月数据分析")
        print("✅ 五维度评价体系 - 盈利能力、成长性、盈利质量、运营效率、偿债风险")
        print("✅ 行业百分位评分 - 确保跨行业可比性")
        print("✅ A~E分级评级 - 专业的投资决策参考")
        print("✅ 多维度Excel报告 - 综合评价、绩优股筛选、统计分析、行业分析")
        print("\n该系统现已具备完整的A股智能选股分析能力!")

    except Exception as e:
        print(f"读取报告失败: {e}")

if __name__ == "__main__":
    show_real_data_report()