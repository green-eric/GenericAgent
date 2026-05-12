#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股智能选股分析系统 v2.0（适配无后缀代码）
"""

import asyncio
import pandas as pd
from datetime import datetime
from finance_data_plugin import (
    get_financial_report,
    analyze_financial_report,
    stock_basic_info
)

class AdvancedStockAnalyzer:
    def __init__(self, input_file: str):
        self.input_file = input_file
        self.batch_size = 3

    def calculate_financial_health(self, report: Dict) -> float:
        """多维度财务健康评分"""
        score = 0.0
        rev_growth = self._calculate_growth(report)
        profit_growth = self._calculate_net_profit_growth(report)
        gross_margin = report.get("gross_profit_margin", 0)
        roe = report.get("roe", 0)

        # 营收增长 (30%)
        if rev_growth > 80: score += 3.0
        elif rev_growth > 50: score += 2.5
        elif rev_growth > 30: score += 2.0
        elif rev_growth > 10: score += 1.0

        # 净利润增长 (25%)
        if profit_growth > 60: score += 2.5
        elif profit_growth > 40: score += 2.0
        elif profit_growth > 20: score += 1.5
        elif profit_growth > 0: score += 1.0

        # 毛利率 (20%)
        if gross_margin > 70: score += 2.0
        elif gross_margin > 50: score += 1.5
        elif gross_margin > 30: score += 1.0

        # ROE (15%)
        if roe > 20: score += 1.5
        elif roe > 15: score += 1.0
        elif roe > 10: score += 0.5

        # 现金流 (10%)
        cash_flow = report.get("operating_cash_flow", 0)
        if cash_flow > 0 and cash_flow > report.get("net_income", 0):
            score += 1.0

        return min(score, 10.0)

    async def get_optimal_report(self, ts_code: str) -> Dict:
        """智能选择最优财报"""
        candidates = []

        # 尝试获取所有可用报告
        for period, rtype in [("2026Q1","quarterly"), ("2025Q4","quarterly"), ("2025","annual")]:
            try:
                report = await get_financial_report(ts_code, rtype, period)
                if report and report.get("total_revenue", 0) > 0:
                    report["report_period"] = period
                    report["report_type"] = rtype
                    candidates.append(report)
            except:
                continue

        if not candidates:
            return None

        # 优先顺序：2026Q1 > 2025Q4 > 2025年报
        priority = {"2026Q1": 3, "2025Q4": 2, "2025": 1}
        return max(candidates, key=lambda x: priority.get(x["report_period"], 0))

    async def analyze_single_stock(self, ts_code: str) -> Dict:
        """单只股票深度分析"""
        try:
            # 自动添加交易所后缀
            if len(ts_code) == 6:
                if ts_code.startswith('6'):
                    full_code = f"{ts_code}.SH"
                else:
                    full_code = f"{ts_code}.SZ"
            else:
                full_code = ts_code

            name = (await stock_basic_info(full_code)).get("name", ts_code)
            report = await self.get_optimal_report(full_code)

            if not report:
                return {"ts_code": ts_code, "error": "无有效财报数据"}

            # AI分析
            analysis = await analyze_financial_report(
                stock_code=full_code,
                report_type=report["report_type"],
                period=report["report_period"],
                model="qwen-max"
            )

            # 计算指标
            rev_growth = self._calculate_growth(report)
            profit_growth = self._calculate_net_profit_growth(report)
            health_score = self.calculate_financial_health(report)

            # 综合评级
            rating = self._generate_rating(rev_growth, health_score, analysis.get("recommendation", ""))

            return {
                "代码": ts_code,
                "名称": name,
                "报告期间": report["report_period"],
                "营收增长率(%)": round(rev_growth, 2),
                "净利润增长率(%)": round(profit_growth, 2),
                "毛利率(%)": round(report.get("gross_profit_margin", 0), 2),
                "ROE(%)": round(report.get("roe", 0), 2),
                "财务健康度": round(health_score, 1),
                "AI评分": analysis.get("score", 0),
                "投资评级": rating,
                "AI摘要": analysis.get("summary", ""),
                "风险提示": "; ".join(analysis.get("risks", [])),
                "操作建议": analysis.get("recommendation", "")
            }
        except Exception as e:
            return {"ts_code": ts_code, "error": str(e)}

    def _calculate_growth(self, report: Dict) -> float:
        """通用增长率计算"""
        try:
            current = report.get("total_revenue", 0)
            if report["report_type"] == "annual":
                prev = report.get("total_revenue_yoy", 0)
            else:
                prev = report.get("total_revenue_qoq", 0)
            return (current - prev) / prev * 100 if prev > 0 else 0
        except:
            return 0.0

    def _calculate_net_profit_growth(self, report: Dict) -> float:
        """净利润增长率"""
        try:
            current = report.get("net_profit", 0)
            prev = report.get("net_profit_yoy", 0)
            return (current - prev) / prev * 100 if prev > 0 else 0
        except:
            return 0.0

    def _generate_rating(self, growth: float, health: float, ai_rec: str) -> str:
        """综合评级逻辑"""
        if growth > 80 and health >= 8:
            return "强烈推荐"
        elif growth > 60 and health >= 7:
            return "推荐"
        elif growth > 50 and health >= 6:
            return "中性"
        elif growth > 30 and health >= 5:
            return "观望"
        else:
            return "回避"

    async def batch_analyze(self) -> pd.DataFrame:
        """执行批量分析"""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            codes = [line.strip() for line in f if line.strip()]

        print(f"🔍 共加载 {len(codes)} 只股票代码")
        results = []

        for i in range(0, len(codes), self.batch_size):
            batch = codes[i:i+self.batch_size]
            print(f"\n🔄 处理第 {i//self.batch_size + 1} 批 ({len(batch)}只)")

            tasks = [self.analyze_single_stock(code) for code in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            valid_results = [r for r in batch_results if isinstance(r, dict) and "error" not in r]
            results.extend(valid_results)

            # 显示高增长股票
            high_growth = [r for r in valid_results if r["营收增长率(%)"] > 50]
            print(f"   📈 高增长({>50%}): {len(high_growth)}只")
            await asyncio.sleep(2)

        df = pd.DataFrame(results)

        # 保存报告到桌面
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        desktop_path = r"C:\Users\green\Desktop"

        df.to_excel(f"{desktop_path}\\A股智能分析报告_{timestamp}.xlsx", index=False)

        # 精选强势股
        strong_buy = df[(df["营收增长率(%)"] > 60) & (df["财务健康度"] >= 7)]
        if not strong_buy.empty:
            strong_buy.to_excel(
                f"{desktop_path}\\强势股_{timestamp}.xlsx",
                index=False,
                columns=[
                    "代码", "名称", "营收增长率(%)",
                    "净利润增长率(%)", "财务健康度", "投资评级"
                ]
            )

        return df

async def main():
    analyzer = AdvancedStockAnalyzer(r"C:\Users\green\Desktop\gy\xuan.txt")
    result_df = await analyzer.batch_analyze()

    if not result_df.empty:
        print(f"\n✅ 分析完成！共处理 {len(result_df)} 只股票")
        print(f"📊 报告已保存到桌面:")
        print(f"   - 完整报告: A股智能分析报告_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx")
        print(f"   - 强势股: 强势股_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx")
    else:
        print("❌ 未获取到有效数据")

if __name__ == "__main__":
    asyncio.run(main())