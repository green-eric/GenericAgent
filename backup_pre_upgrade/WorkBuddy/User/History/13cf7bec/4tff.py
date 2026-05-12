#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读取并展示A股智能选股分析系统生成的Excel报告
"""

import pandas as pd
from openpyxl import load_workbook

def read_excel_report():
    """读取Excel报告并显示关键信息"""
    try:
        # 读取主结果表
        df_main = pd.read_excel('C:\\Users\\green\\Desktop\\股票业绩评价_20260424_2047.xlsx', sheet_name='综合评价结果')

        # 读取绩优股表（如果存在）
        try:
            df_a_stocks = pd.read_excel('C:\\Users\\green\\Desktop\\股票业绩评价_20260424_2047.xlsx', sheet_name='绩优股(A级')
            print("=== A级绩优股 (前10只) ===")
            print(df_a_stocks.head(10).to_string(index=False))
            print(f"\nA级股票总数: {len(df_a_stocks)}")
        except:
            print("未找到A级绩优股表格")

        # 读取统计概览
        try:
            df_stats = pd.read_excel('C:\\Users\\green\\Desktop\\股票业绩评价_20260424_2047.xlsx', sheet_name='统计概览')
            print("\n=== 统计分析 ===")
            print(df_stats.to_string(index=False))
        except:
            print("未找到统计概览表格")

        # 显示总体统计信息
        print(f"\n=== 总体统计 ===")
        print(f"总分析股票数: {len(df_main)}")
        print(f"A级股票数量: {len(df_main[df_main['评级'] == 'A'])}")
        print(f"B级股票数量: {len(df_main[df_main['评级'] == 'B'])}")
        print(f"C级股票数量: {len(df_main[df_main['评级'] == 'C'])}")
        print(f"D级股票数量: {len(df_main[df_main['评级'] == 'D'])}")
        print(f"E级股票数量: {len(df_main[df_main['评级'] == 'E'])}")

        # 显示评分分布
        print(f"\n=== 评分分布 ===")
        avg_score = df_main['总评分'].mean()
        max_score = df_main['总评分'].max()
        min_score = df_main['总评分'].min()
        print(f"平均总评分: {avg_score:.2f}")
        print(f"最高总评分: {max_score:.2f}")
        print(f"最低总评分: {min_score:.2f}")

        # 按行业统计
        print(f"\n=== 各行业统计 ===")
        industry_stats = df_main.groupby('行业').agg({
            '股票代码': 'count',
            '总评分': ['mean', 'max']
        }).round(2)
        industry_stats.columns = ['股票数量', '平均评分', '最高评分']
        print(industry_stats.sort_values('平均评分', ascending=False))

    except Exception as e:
        print(f"读取报告失败: {e}")

if __name__ == "__main__":
    read_excel_report()