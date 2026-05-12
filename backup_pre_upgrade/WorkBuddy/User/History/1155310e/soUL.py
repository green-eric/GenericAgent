#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股智能选股分析系统 - 终极版
功能：动态获取股票年报季报数据，筛选增长率>50%的股票，生成专业Excel报告

作者：AI助手
日期：2026-04-24
"""

import os
import sys
import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# 导入东方财富金融工具集
sys.path.append(os.path.expanduser('~/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/neodata-financial-search'))
from scripts.query import query_financial_data

class UltimateStockAnalyzer:
    """终极版A股智能选股分析器"""

    def __init__(self):
        self.current_date = datetime.now()
        self.year = self.current_date.year
        self.month = self.current_date.month

        # 科创板股票代码前缀
        self.kcb_prefixes = ['688', '430']

        # 财务评分体系权重
        self.scoring_weights = {
            '成长能力': 0.40,
            '盈利能力': 0.30,
            '业绩趋势': 0.30
        }

        # 财务指标权重
        self.indicator_weights = {
            '净利润增速': 0.60,  # 成长能力子项
            '营收增速': 0.40,   # 成长能力子项
            'ROE': 0.60,        # 盈利能力子项
            '预告类型': 0.60    # 业绩趋势子项
        }

        # 数据存储
        self.stock_data = []
        self.filtered_stocks = []

    def is_kcb_stock(self, stock_code: str) -> bool:
        """判断是否为科创板股票"""
        code_prefix = stock_code[:3]
        return code_prefix in self.kcb_prefixes

    def get_dynamic_date_params(self) -> Dict[str, str]:
        """获取动态日期参数"""
        # 判断当前季度和年份
        quarter = (self.month - 1) // 3 + 1

        if quarter == 1:  # Q1 (1-3月)
            report_year = self.year - 1
            report_type = '年报'
            quarter_type = '一季报' if self.month >= 4 else '无季报'
        elif quarter == 2:  # Q2 (4-6月)
            report_year = self.year
            report_type = '一季报'
            quarter_type = '一季报'
        elif quarter == 3:  # Q3 (7-9月)
            report_year = self.year
            report_type = '半年报'
            quarter_type = '三季报'
        else:  # Q4 (10-12月)
            report_year = self.year
            report_type = '三季报'
            quarter_type = '三季报'

        return {
            'report_year': str(report_year),
            'report_type': report_type,
            'quarter_type': quarter_type,
            'current_year': str(self.year),
            'current_month': f"{self.month:02d}"
        }

    async def fetch_stock_basic_info(self) -> List[Dict]:
        """获取股票基本信息"""
        try:
            result = await query_financial_data(
                query="A股股票列表",
                data_type="api"
            )

            stocks = []
            if result and 'data' in result and 'apiData' in result['data']:
                api_data = result['data']['apiData']
                if 'entity' in api_data:
                    for item in api_data['entity']:
                        if len(item) >= 2:
                            stock_code = item[0]
                            stock_name = item[1]

                            # 排除科创板
                            if not self.is_kcb_stock(stock_code):
                                stocks.append({
                                    'code': stock_code,
                                    'name': stock_name,
                                    'is_kcb': False
                                })

            print(f"✅ 成功获取 {len(stocks)} 只非科创板A股股票信息")
            return stocks

        except Exception as e:
            print(f"❌ 获取股票基本信息失败: {e}")
            return []

    async def calculate_growth_rate(self, current_data: Dict) -> Dict:
        """计算增长率和财务评分"""
        try:
            # 获取最新财报数据
            income_query = f"{current_data['name']} {current_data.get('report_year', '2025')}年利润表"

            result = await query_financial_data(
                query=income_query,
                data_type="api"
            )

            growth_rates = {}
            financial_scores = {}

            if result and 'data' in result and 'apiData' in result['data']:
                api_data = result['data']['apiData']
                if 'apiRecall' in api_data:
                    for recall_item in api_data['apiRecall']:
                        if 'desc' in recall_item and 'content' in recall_item:
                            content = recall_item['content']

                            # 提取关键财务指标
                            net_profit_yoy = self._extract_percentage(content, '净利润同比增长')
                            revenue_yoy = self._extract_percentage(content, '营业收入同比增长')
                            roe = self._extract_percentage(content, '净资产收益率')

                            # 计算增长率
                            if net_profit_yoy:
                                growth_rates['净利润增速'] = net_profit_yoy
                            if revenue_yoy:
                                growth_rates['营收增速'] = revenue_yoy
                            if roe:
                                growth_rates['ROE'] = roe

                            # 计算财务评分
                            performance_score = self._calculate_performance_score(
                                net_profit_yoy, revenue_yoy, roe
                            )
                            financial_scores['综合评分'] = performance_score

            # 补充缺失的数据
            for key in ['净利润增速', '营收增速', 'ROE']:
                if key not in growth_rates:
                    growth_rates[key] = 0.0

            return {
                **growth_rates,
                **financial_scores,
                '筛选状态': '通过' if any(growth > 50 for growth in [growth_rates.get('净利润增速', 0), growth_rates.get('营收增速', 0)]) else '未通过'
            }

        except Exception as e:
            print(f"❌ 计算增长率失败: {e}")
            return {
                '净利润增速': 0.0,
                '营收增速': 0.0,
                'ROE': 0.0,
                '综合评分': 0.0,
                '筛选状态': '数据获取失败'
            }

    def _extract_percentage(self, text: str, keyword: str) -> float:
        """从文本中提取百分比数值"""
        try:
            lines = text.split('\n')
            for line in lines:
                if keyword in line:
                    # 查找百分比
                    import re
                    percent_match = re.search(r'(\d+\.?\d*)%', line)
                    if percent_match:
                        return float(percent_match.group(1))
            return 0.0
        except:
            return 0.0

    def _calculate_performance_score(self, net_profit_yoy: float, revenue_yoy: float, roe: float) -> float:
        """计算业绩评分"""
        try:
            # 成长能力得分 (40%)
            growth_score = min((net_profit_yoy * 0.6 + revenue_yoy * 0.4), 100)

            # 盈利能力得分 (30%)
            profit_score = min(roe, 30)  # ROE超过30%按30分计

            # 业绩趋势得分 (30%)
            trend_score = 50  # 基础分，可根据预告类型调整

            total_score = (
                growth_score * self.scoring_weights['成长能力'] +
                profit_score * self.scoring_weights['盈利能力'] +
                trend_score * self.scoring_weights['业绩趋势']
            )

            return round(total_score, 2)

        except:
            return 0.0

    async def analyze_all_stocks(self) -> List[Dict]:
        """分析所有股票"""
        print("🚀 开始全量股票分析...")

        # 获取股票列表
        stock_list = await self.fetch_stock_basic_info()

        if not stock_list:
            print("❌ 未获取到股票列表")
            return []

        analysis_results = []

        for i, stock in enumerate(stock_list):
            print(f"📊 正在分析 {i+1}/{len(stock_list)}: {stock['name']}({stock['code']})")

            # 获取财务数据并计算增长率
            growth_data = await self.calculate_growth_rate(stock)

            # 合并数据
            stock_result = {
                '股票代码': stock['code'],
                '股票名称': stock['name'],
                '是否科创板': stock['is_kcb'],
                **growth_data
            }

            analysis_results.append(stock_result)

            # 添加延迟避免请求过于频繁
            await asyncio.sleep(0.5)

        print(f"✅ 完成所有股票分析，共处理 {len(analysis_results)} 只股票")
        return analysis_results

    def filter_high_growth_stocks(self, all_results: List[Dict]) -> List[Dict]:
        """筛选高增长股票（增长率>50%）"""
        filtered = []

        for result in all_results:
            # 筛选条件：净利润增速或营收增速大于50%
            net_profit_growth = result.get('净利润增速', 0)
            revenue_growth = result.get('营收增速', 0)

            if net_profit_growth > 50 or revenue_growth > 50:
                # 添加详细标注
                result['增长率标识'] = '净利润>50%' if net_profit_growth > 50 else '营收>50%'
                result['推荐等级'] = '强力推荐' if net_profit_growth > 80 or revenue_growth > 80 else '重点关注'

                filtered.append(result)

        # 按综合评分排序
        filtered.sort(key=lambda x: x.get('综合评分', 0), reverse=True)

        return filtered

    def generate_excel_report(self, all_results: List[Dict], filtered_results: List[Dict]):
        """生成Excel报告"""
        try:
            # 创建工作簿
            with pd.ExcelWriter('股票增长率分析_终极版.xlsx', engine='xlsxwriter') as writer:

                # 完整分析结果表
                all_df = pd.DataFrame(all_results)
                all_df.to_excel(writer, sheet_name='完整分析结果', index=False)

                # 高增长股票筛选结果
                filtered_df = pd.DataFrame(filtered_results)
                filtered_df.to_excel(writer, sheet_name='高增长股票', index=False)

                # 统计信息工作表
                stats_data = self._generate_statistics(all_results, filtered_results)
                stats_df = pd.DataFrame([stats_data])
                stats_df.to_excel(writer, sheet_name='统计分析', index=False)

                # 格式化工作簿
                workbook = writer.book

                # 设置格式
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#D7E4BC',
                    'border': 1
                })

                # 格式化数字列
                number_format = workbook.add_format({'num_format': '0.00'})

                # 应用格式到各个工作表
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]

                    # 设置标题格式
                    for col_num, value in enumerate(all_df.columns.values if sheet_name == '完整分析结果' else filtered_df.columns.values):
                        worksheet.write(0, col_num, value, header_format)

                    # 设置数字格式
                    numeric_cols = ['净利润增速', '营收增速', 'ROE', '综合评分']
                    for col in numeric_cols:
                        if col in worksheet.row(0):
                            col_idx = worksheet.row(0).index(col)
                            worksheet.set_column(col_idx, col_idx, 12, number_format)

            print("✅ Excel报告已生成: 股票增长率分析_终极版.xlsx")
            return True

        except Exception as e:
            print(f"❌ 生成Excel报告失败: {e}")
            return False

    def _generate_statistics(self, all_results: List[Dict], filtered_results: List[Dict]) -> Dict:
        """生成统计数据"""
        total_stocks = len(all_results)
        high_growth_count = len(filtered_results)
        kcb_count = sum(1 for r in all_results if r.get('是否科创板', False))

        avg_net_profit_growth = np.mean([r.get('净利润增速', 0) for r in filtered_results])
        avg_revenue_growth = np.mean([r.get('营收增速', 0) for r in filtered_results])
        avg_score = np.mean([r.get('综合评分', 0) for r in filtered_results])

        return {
            '分析日期': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '总股票数量': total_stocks,
            '排除科创板数量': kcb_count,
            '高增长股票数量': high_growth_count,
            '高增长股票占比': f"{(high_growth_count/total_stocks)*100:.1f}%" if total_stocks > 0 else "0%",
            '平均净利润增速': f"{avg_net_profit_growth:.2f}%",
            '平均营收增速': f"{avg_revenue_growth:.2f}%",
            '平均综合评分': f"{avg_score:.2f}",
            '数据来源': '东方财富金融工具集',
            '筛选标准': '净利润增速>50% 或 营收增速>50%'
        }

    async def run_complete_analysis(self):
        """运行完整分析流程"""
        print("🎯 A股智能选股分析系统 - 终极版启动")
        print(f"📅 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 动态参数: {self.get_dynamic_date_params()}")

        # 步骤1: 获取所有股票数据
        print("\n🔍 步骤1: 获取股票基本信息...")
        all_stock_data = await self.analyze_all_stocks()

        if not all_stock_data:
            print("❌ 未能获取股票数据，分析终止")
            return

        # 步骤2: 筛选高增长股票
        print("\n🎯 步骤2: 筛选高增长股票...")
        high_growth_stocks = self.filter_high_growth_stocks(all_stock_data)

        print(f"✅ 筛选完成: 从 {len(all_stock_data)} 只股票中筛选出 {len(high_growth_stocks)} 只高增长股票")

        # 步骤3: 生成Excel报告
        print("\n📋 步骤3: 生成Excel分析报告...")
        success = self.generate_excel_report(all_stock_data, high_growth_stocks)

        if success:
            print("\n🎉 分析完成!")
            print(f"📈 共分析 {len(all_stock_data)} 只A股股票")
            print(f"🎯 筛选出 {len(high_growth_stocks)} 只增长率>50%的股票")
            print(f"📊 报告已保存为: 股票增长率分析_终极版.xlsx")
        else:
            print("❌ 报告生成失败")


async def main():
    """主函数"""
    analyzer = UltimateStockAnalyzer()
    await analyzer.run_complete_analysis()


if __name__ == "__main__":
    asyncio.run(main())