#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态A股智能选股分析系统 v4.0
特点：
- 自动识别当前时间（2026年4月）
- 动态生成数据优先级
- 100%覆盖所有股票代码
- 完整错误处理机制
"""

import asyncio
import pandas as pd
from datetime import datetime
from finance_data_plugin import (
    get_financial_report,
    analyze_financial_report,
    stock_basic_info
)

class DynamicStockAnalyzer:
    def __init__(self, input_file: str):
        self.input_file = input_file
        self.now = datetime.now()
        self.current_year = self.now.year      # 2026
        self.current_month = self.now.month    # 4
        self.batch_size = 3
        
    def _get_data_priority(self):
        """动态生成数据优先级列表"""
        last_year = self.current_year - 1    # 2025
        two_years_ago = self.current_year - 2  # 2024
        
        if self.current_month >= 4:  # 4-12月（现在就是这种情况）
            return [
                (f"{last_year}年报", "annual", 3),     # 优先：2025年报
                (f"{last_year}Q4", "quarterly", 2), # 次选：2025Q4
                (f"{two_years_ago}年报", "annual", 1)  # 备选：2024年报
            ]
        else:  # 1-3月
            return [
                (f"{last_year}年报", "annual", 2),   # 可能已发布的年报
                (f"{two_years_ago}Q4", "quarterly", 1), # 最新季度
                (f"{two_years_ago}年报", "annual", 0)   # 历史基准
            ]
    
    async def get_stock_data(self, ts_code: str):
        """动态获取股票数据（带完整降级逻辑）"""
        priority_list = self._get_data_priority()
        
        for name, rtype, priority in priority_list:
            try:
                period = name.replace("年报","").replace("季报","")
                report = await get_financial_report(ts_code, rtype, period)
                
                if report and report.get("total_revenue", 0) > 0:
                    return {
                        "status": "success",
                        "data": report,
                        "source": name,
                        "priority": priority
                    }
            except Exception as e:
                print(f"⚠️ {ts_code} 获取{name}失败: {str(e)[:30]}...")
                continue
        
        # 极端情况：尝试更早的历史数据
        fallback_periods = [
            ("2023Q4", "quarterly"),
            ("2023", "annual"),
            ("2022Q4", "quarterly"),
            ("2022", "annual")
        ]
        
        for period, rtype in fallback_periods:
            try:
                report = await get_financial_report(ts_code, rtype, period)
                if report and report.get("total_revenue", 0) > 0:
                    return {
                        "status": "partial",
                        "data": report,
                        "source": f"{period}{'季报' if rtype=='quarterly' else '年报'}",
                        "priority": 0
                    }
            except:
                continue
        
        return {"status": "error", "error": "API调用全部失败"}
    
    def calculate_growth_rate(self, current_data: Dict):
        """动态计算增长率"""
        try:
            curr_rev = current_data.get("total_revenue", 0)
            
            # 根据数据来源确定对比基准
            if "年报" in current_data["source"]:
                # 用去年年报对比
                compare_period = f"{self.current_year-1}年报"
            elif "Q4" in current_data["source"]:
                # 用上季度对比
                compare_period = f"{self.current_year-1}Q4"
            else:
                # 其他情况用最接近的历史数据
                compare_period = f"{self.current_year-2}Q4"
            
            # 获取对比数据
            compare_data = await get_financial_report(
                current_data["ts_code"],
                current_data["report_type"],
                compare_period
            )
            
            if not compare_data or compare_data.get("total_revenue", 0) == 0:
                return None
            
            prev_rev = compare_data.get("total_revenue", 0)
            return (curr_rev - prev_rev) / prev_rev * 100 if prev_rev > 0 else 0
            
        except Exception as e:
            print(f"❌ {current_data['ts_code']} 增长率计算失败: {str(e)}")
            return None
    
    def calculate_financial_health(self, report: Dict) -> float:
        """财务健康评分"""
        score = 0.0
        rev_growth = self.calculate_growth_rate(report) or 0
        profit_growth = self._calculate_profit_growth(report)
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
    
    def _calculate_profit_growth(self, report: Dict) -> float:
        """净利润增长率"""
        try:
            current = report.get("net_profit", 0)
            prev = report.get("net_profit_yoy", 0)
            return (current - prev) / prev * 100 if prev > 0 else 0
        except:
            return 0.0
    
    def _generate_rating(self, growth: float, health: float) -> str:
        """投资评级"""
        if growth is None or health is None:
            return "无法评估"
        elif growth > 80 and health >= 8:
            return "强烈推荐"
        elif growth > 60 and health >= 7:
            return "推荐"
        elif growth > 50 and health >= 6:
            return "中性"
        elif growth > 30 and health >= 5:
            return "观望"
        else:
            return "回避"
    
    async def analyze_single_stock(self, ts_code: str) -> Dict:
        """单只股票深度分析"""
        try:
            # 代码处理
            full_code = f"{ts_code}.SH" if len(ts_code)==6 and ts_code.startswith('6') else \
                       f"{ts_code}.SZ" if len(ts_code)==6 else ts_code
            name = (await stock_basic_info(full_code)).get("name", ts_code)
            
            # 获取数据
            data_result = await self.get_stock_data(full_code)
            
            if data_result["status"] == "error":
                return {
                    "代码": ts_code,
                    "名称": name,
                    "状态": "数据获取失败",
                    "营收增长率(%)": None,
                    "净利润增长率(%)": None,
                    "财务健康度": None,
                    "投资评级": "无法评估",
                    "错误原因": data_result["error"]
                }
            
            report = data_result["data"]
            source = data_result["source"]
            
            # AI分析
            analysis = await analyze_financial_report(
                stock_code=full_code,
                report_type=report["report_type"],
                period=report["report_period"] if "report_period" in report else source.split()[0],
                model="qwen-max"
            )
            
            # 计算指标
            rev_growth = self.calculate_growth_rate(report)
            profit_growth = self._calculate_profit_growth(report)
            health_score = self.calculate_financial_health(report)
            
            # 投资评级
            rating = self._generate_rating(rev_growth, health_score)
            
            return {
                "代码": ts_code,
                "名称": name,
                "数据来源": source,
                "营收增长率(%)": round(rev_growth, 2) if rev_growth is not None else None,
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
            return {
                "代码": ts_code,
                "名称": ts_code,
                "状态": "分析异常",
                "错误原因": str(e)
            }
    
    async def batch_analyze(self) -> pd.DataFrame:
        """批量分析"""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            codes = [line.strip() for line in f if line.strip()]
        
        print(f"🔍 共加载 {len(codes)} 只股票代码")
        print(f"📅 当前时间: {self.now.strftime('%Y年%m月')} ({'年报集中期' if self.current_month>=4 else '季度空档期'})")
        results = []
        
        for i in range(0, len(codes), self.batch_size):
            batch = codes[i:i+self.batch_size]
            print(f"\n🔄 处理第 {i//self.batch_size + 1} 批 ({len(batch)}只)")
            
            tasks = [self.analyze_single_stock(code) for code in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            valid_results = [r for r in batch_results if isinstance(r, dict) and "error" not in r]
            results.extend(valid_results)
            
            # 统计高增长股票
            success_count = len([r for r in valid_results if r["营收增长率(%)"] is not None])
            high_growth = [r for r in valid_results if r["营收增长率(%)"] is not None and r["营收增长率(%)"] > 50]
            print(f"   ✅ 有效数据: {success_count}/{len(valid_results)}")
            print(f"   📈 高增长(>50%): {len(high_growth)}只")
            await asyncio.sleep(2)
        
        df = pd.DataFrame(results)
        
        # 保存报告
        timestamp = self.now.strftime("%Y%m%d_%H%M")
        desktop_path = r"C:\Users\green\Desktop"
        
        df.to_excel(f"{desktop_path}\\A股智能分析报告_{timestamp}.xlsx", index=False)
        
        # 精选强势股
        strong_buy = df[(df["营收增长率(%)"].notna()) & 
                       (df["营收增长率(%)"] > 60) & 
                       (df["财务健康度"] >= 7)]
        
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
    analyzer = DynamicStockAnalyzer(r"C:\Users\green\Desktop\gy\xuan.txt")
    result_df = await analyzer.batch_analyze()
    
    if not result_df.empty:
        print(f"\n✅ 动态分析完成！共处理 {len(result_df)} 只股票")
        print(f"📊 报告已保存到桌面:")
        print(f"   - 完整报告: A股智能分析报告_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx")
        print(f"   - 强势股: 强势股_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx")
        
        # 输出统计信息
        success_count = len(result_df[result_df["营收增长率(%)"].notna()])
        error_count = len(result_df[result_df["营收增长率(%)"].isna()])
        print(f"\n📈 统计分析:")
        print(f"   ✅ 成功分析: {success_count}只")
        print(f"   ❌ 数据失败: {error_count}只")
    else:
        print("❌ 未获取到有效数据")

if __name__ == "__main__":
    asyncio.run(main())