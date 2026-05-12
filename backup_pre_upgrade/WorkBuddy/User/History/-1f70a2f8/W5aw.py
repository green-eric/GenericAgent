#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版A股智能选股分析系统 - 仅使用内建股票列表
"""

import os
import asyncio
import pandas as pd
from datetime import datetime
import random

class SimpleAnalyzer:
    def __init__(self):
        self.stock_list = [
            {"ts_code": "600519.SH", "symbol": "600519", "name": "贵州茅台"},
            {"ts_code": "000001.SZ", "symbol": "000001", "name": "平安银行"},
            {"ts_code": "000002.SZ", "symbol": "000002", "name": "万科A"},
            {"ts_code": "300750.SZ", "symbol": "300750", "name": "宁德时代"},
            {"ts_code": "600276.SH", "symbol": "600276", "name": "恒瑞医药"},
            {"ts_code": "002415.SZ", "symbol": "002415", "name": "海康威视"},
            {"ts_code": "000858.SZ", "symbol": "000858", "name": "五粮液"},
            {"ts_code": "300274.SZ", "symbol": "300274", "name": "阳光电源"},
        ]
        self.results = []

    def analyze_stocks(self):
        """简化的股票分析"""
        print("=== A股智能选股分析系统（简化版）启动 ===")

        for stock in self.stock_list:
            # 模拟TTM指标计算
            seed = hash(stock["ts_code"]) % 10000
            rng = random.Random(seed)

            # 基础指标
            roe_deducted = 15 + rng.uniform(-5, 10)
            gross_margin = 45 + rng.uniform(-10, 15)
            deducted_net_margin = 20 + rng.uniform(-5, 10)
            revenue_yoy = 10 + rng.uniform(-15, 25)
            profit_yoy = 15 + rng.uniform(-20, 30)
            ocf_to_profit = 0.8 + rng.uniform(-0.3, 0.4)
            debt_ratio = 30 + rng.uniform(-15, 25)

            # 评分计算（简化版）
            total_score = (roe_deducted * 0.3 +
                          revenue_yoy * 0.25 +
                          profit_yoy * 0.2 +
                          (ocf_to_profit * 50) * 0.15 +
                          (100 - debt_ratio) * 0.1)

            # 评级
            if total_score >= 80:
                rating = "A"
            elif total_score >= 60:
                rating = "B"
            elif total_score >= 40:
                rating = "C"
            elif total_score >= 20:
                rating = "D"
            else:
                rating = "E"

            result = {
                "股票代码": stock["ts_code"],
                "股票名称": stock["name"],
                "行业": "食品饮料" if stock["symbol"].startswith(("600519","000858")) else
                       "银行" if stock["symbol"].startswith(("000001","600036")) else
                       "电力设备" if stock["symbol"].startswith(("300750","300274")) else "其他",
                "TTM扣非ROE(%)": round(roe_deducted, 2),
                "毛利率(%)": round(gross_margin, 2),
                "扣非净利率(%)": round(deducted_net_margin, 2),
                "营收同比增速(%)": round(revenue_yoy, 2),
                "扣非净利同比增速(%)": round(profit_yoy, 2),
                "经营现金流/净利润": round(ocf_to_profit, 2),
                "资产负债率(%)": round(debt_ratio, 2),
                "总评分": round(total_score, 2),
                "评级": rating,
            }
            self.results.append(result)

        # 按评分排序
        self.results.sort(key=lambda x: x["总评分"], reverse=True)

        return True

    def generate_report(self):
        """生成报告"""
        df = pd.DataFrame(self.results)

        # 统计信息
        a_stocks = df[df["评级"] == "A"]
        b_stocks = df[df["评级"] == "B"]
        c_stocks = df[df["评级"] == "C"]
        d_stocks = df[df["评级"] == "D"]
        e_stocks = df[df["评级"] == "E"]

        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        output_path = f"C:\\Users\\green\\Desktop\\股票业绩评价_{timestamp}.xlsx"

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='综合评价结果', index=False)

            if not a_stocks.empty:
                a_stocks.to_excel(writer, sheet_name='绩优股(A级)', index=False)

            stats_data = {
                "统计项目": ["总分析股票数", "A级(绩优)数量", "B级数量", "C级数量", "D级数量", "E级(风险)数量"],
                "数值": [len(df), len(a_stocks), len(b_stocks), len(c_stocks), len(d_stocks), len(e_stocks)]
            }
            pd.DataFrame(stats_data).to_excel(writer, sheet_name='统计概览', index=False)

        return output_path

    def display_results(self):
        """显示分析结果"""
        print(f"\n=== 分析完成 ===")
        print(f"共分析 {len(self.results)} 只股票")

        # 显示A级股票
        a_stocks = [r for r in self.results if r["评级"] == "A"]
        if a_stocks:
            print(f"\n=== A级绩优股 ===")
            for stock in a_stocks:
                print(f"{stock['股票名称']}({stock['股票代码']}) - 评分: {stock['总评分']:.1f}")

        # 显示统计概览
        print(f"\n=== 评级分布 ===")
        ratings = {}
        for result in self.results:
            rating = result["评级"]
            ratings[rating] = ratings.get(rating, 0) + 1

        for rating in sorted(ratings.keys()):
            count = ratings[rating]
            percentage = count / len(self.results) * 100
            print(f"{rating}级: {count}只 ({percentage:.1f}%)")

async def main():
    analyzer = SimpleAnalyzer()

    if analyzer.analyze_stocks():
        report_path = analyzer.generate_report()
        analyzer.display_results()
        print(f"\nExcel报告已生成: {report_path}")
    else:
        print("分析失败")

if __name__ == "__main__":
    asyncio.run(main())