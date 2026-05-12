#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股智能选股分析系统 - 基于多维度业绩评价方案
功能：动态获取股票TTM财务数据，行业百分位评分，生成专业Excel分析报告
按建议方案：盈利能力、成长性、盈利质量、运营效率、偿债风险五维度
"""

import os
import sys
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import random

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AStockAnalyzer:
    """A股智能选股分析器 - 业绩评价方案版"""

    def __init__(self):
        self.stock_list = []          # 股票基本信息列表
        self.financial_data = {}      # 存储每只股票的原始季报数据
        self.ttm_metrics = {}         # 各股票TTM指标
        self.scores = {}              # 各股票评分
        self.results = []             # 最终结果
        self.current_date = datetime.now()
        self.current_year = self.current_date.year
        self.current_month = self.current_date.month

        # 行业映射（简化版，实际应从分类数据获取）
        self.industry_map = self._build_industry_map()

        logger.info(f"初始化分析器 - 年份: {self.current_year}, 月份: {self.current_month}")

    def _build_industry_map(self) -> Dict[str, str]:
        """构建股票代码到行业的简易映射（按代码特征）"""
        # 实际应用中可接入申万行业分类数据
        mapping = {
            "600519": "食品饮料",
            "000858": "食品饮料",
            "000568": "食品饮料",
            "000001": "银行",
            "600036": "银行",
            "601398": "银行",
            "000002": "房地产",
            "600048": "房地产",
            "001979": "房地产",
            "300750": "电力设备",
            "300274": "电力设备",
            "300014": "电力设备",
            "600276": "医药生物",
            "300760": "医药生物",
            "000538": "医药生物",
            "002415": "计算机",
            "300033": "计算机",
            "000063": "通信",
            "600887": "食品饮料",
        }
        return mapping

    def load_stock_list(self) -> bool:
        """加载股票列表（从文件读取，支持多种格式）"""
        try:
            stock_list_file = "C:\\Users\\green\\Desktop\\gy\\xuan.txt"
            if not os.path.exists(stock_list_file):
                logger.error(f"股票列表文件不存在: {stock_list_file}")
                # 使用内建示例列表以便演示
                logger.info("使用内建示例股票列表")
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
                return True

            self.stock_list = []
            with open(stock_list_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # 支持“代码:名称”或“代码 名称”格式
                    if ':' in line:
                        parts = line.split(':', 1)
                    elif ' ' in line:
                        parts = line.split(' ', 1)
                    else:
                        continue
                    if len(parts) != 2:
                        continue
                    ts_code = parts[0].strip()
                    name = parts[1].strip()
                    # 过滤科创板（可根据需要调整）
                    if ts_code.startswith('688') or ts_code.startswith('430'):
                        continue
                    exchange_suffix = '.SZ' if ts_code.startswith(('0','3')) else '.SH'
                    full_code = ts_code + exchange_suffix
                    self.stock_list.append({
                        "ts_code": full_code,
                        "symbol": ts_code,
                        "name": name
                    })
            logger.info(f"成功加载 {len(self.stock_list)} 只股票")
            return True
        except Exception as e:
            logger.error(f"加载股票列表失败: {e}")
            return False

    def _get_industry(self, symbol: str) -> str:
        """获取股票行业，未匹配时返回'其他'"""
        return self.industry_map.get(symbol, "其他")

    async def get_quarterly_financials(self, ts_code: str, symbol: str, name: str) -> Optional[Dict]:
        """
        获取单只股票近8个季度财务数据（模拟实现，可替换为真实接口）
        返回包含各季度主要财务指标的字典
        """
        try:
            await asyncio.sleep(0.05)  # 模拟网络延迟

            # 使用股票代码生成固定随机种子，保证数据可重复
            seed = hash(ts_code) % 10000
            rng = random.Random(seed)
            industry = self._get_industry(symbol)

            # 根据行业设定基础参数
            if industry == "食品饮料":
                base_profit = 30 + rng.randint(-5, 10)
                base_revenue = 100 + rng.randint(-10, 20)
                base_asset_turnover = 0.8
                base_margin = 0.45
            elif industry == "银行":
                base_profit = 200 + rng.randint(-20, 50)
                base_revenue = 500 + rng.randint(-30, 50)
                base_asset_turnover = 0.03
                base_margin = 0.35
            elif industry == "房地产":
                base_profit = 15 + rng.randint(-5, 10)
                base_revenue = 80 + rng.randint(-15, 20)
                base_asset_turnover = 0.25
                base_margin = 0.12
            elif industry == "电力设备":
                base_profit = 20 + rng.randint(-8, 15)
                base_revenue = 60 + rng.randint(-10, 15)
                base_asset_turnover = 0.6
                base_margin = 0.18
            elif industry == "医药生物":
                base_profit = 18 + rng.randint(-5, 12)
                base_revenue = 50 + rng.randint(-10, 15)
                base_asset_turnover = 0.7
                base_margin = 0.25
            else:  # 其他行业
                base_profit = 10 + rng.randint(-5, 15)
                base_revenue = 40 + rng.randint(-10, 20)
                base_asset_turnover = 0.5
                base_margin = 0.15

            # 模拟近8个季度数据（从当前往前推8个季度）
            quarters = []
            # 以当前年月确定最新已披露的季度末
            latest_quarter = ((self.current_month - 1) // 3) * 3  # 3,6,9,12
            latest_date = datetime(self.current_year, latest_quarter, 30)
            # 确保不超过当前日期（若当月刚结束可以算上一季度）
            for i in range(7, -1, -1):
                q_end = latest_date - timedelta(days=90 * i)
                # 模拟每个季度的数据，加入缓慢增长趋势和季节性
                growth_factor = 1 + 0.02 * (7 - i)  # 越近的季度基数略高
                seasonal = 1 + 0.05 * np.sin(np.pi * (q_end.month % 12) / 6)  # 年中和年末略高
                noise = rng.uniform(-0.05, 0.05)

                revenue = base_revenue * growth_factor * seasonal * (1 + noise)
                net_profit = revenue * base_margin * (1 + noise * 0.5)
                # 扣非净利润等于净利润的95% - 105%
                deducted_profit = net_profit * rng.uniform(0.95, 1.05)
                # 经营现金流波动较大
                ocf = net_profit * rng.uniform(0.7, 1.4)
                total_assets = revenue / base_asset_turnover * rng.uniform(0.9, 1.1)
                net_equity = total_assets * rng.uniform(0.3, 0.7)  # 资产负债率30%-70%
                total_liability = total_assets - net_equity
                interest_bearing_debt = total_liability * rng.uniform(0.4, 0.7)
                interest_expense = interest_bearing_debt * 0.03  # 假设平均利率3%
                receivables = revenue * rng.uniform(0.1, 0.3)  # 应收账款占收入比
                inventory = revenue * rng.uniform(0.2, 0.5) if industry != "银行" else 0

                quarters.append({
                    "report_date": q_end.strftime('%Y-%m-%d'),
                    "revenue": round(revenue, 2),
                    "net_profit": round(net_profit, 2),
                    "deducted_profit": round(deducted_profit, 2),
                    "operating_cash_flow": round(ocf, 2),
                    "total_assets": round(total_assets, 2),
                    "net_equity": round(net_equity, 2),
                    "total_liability": round(total_liability, 2),
                    "interest_expense": round(interest_expense, 2),
                    "receivables": round(receivables, 2),
                    "inventory": round(inventory, 2),
                })

            # 返回8个季度数据（按时间升序）
            return {
                "ts_code": ts_code,
                "symbol": symbol,
                "name": name,
                "industry": industry,
                "quarters": quarters
            }

        except Exception as e:
            logger.warning(f"获取 {name}({ts_code}) 财务数据失败: {e}")
            return None

    def calculate_ttm_metrics(self, stock_data: Dict) -> Dict:
        """
        基于最近四个季度计算TTM指标
        返回所有评价维度所需的TTM指标字典
        """
        quarters = stock_data["quarters"]
        if len(quarters) < 4:
            logger.warning(f"{stock_data['ts_code']} 季度数据不足，无法计算TTM")
            return {}

        # 最近四个季度
        recent_4q = quarters[-4:]
        # 前一期四个季度（用于计算同比增速）
        prev_4q = quarters[-8:-4] if len(quarters) >= 8 else None

        # 汇总TTM数据
        ttm_revenue = sum(q["revenue"] for q in recent_4q)
        ttm_net_profit = sum(q["net_profit"] for q in recent_4q)
        ttm_deducted_profit = sum(q["deducted_profit"] for q in recent_4q)
        ttm_ocf = sum(q["operating_cash_flow"] for q in recent_4q)

        # 取最新季度资产负债表数据近似TTM（实务也可用最新一期）
        latest_q = recent_4q[-1]
        total_assets = latest_q["total_assets"]
        net_equity = latest_q["net_equity"]
        total_liability = latest_q["total_liability"]
        receivables = latest_q["receivables"]
        inventory = latest_q["inventory"]
        interest_expense = sum(q["interest_expense"] for q in recent_4q)

        # 计算各指标
        # 盈利能力
        avg_equity = net_equity  # 简化；更好应用期初期末平均
        roe_deducted = (ttm_deducted_profit / avg_equity * 100) if avg_equity > 0 else 0
        # 毛利率 = (收入 - 成本) / 收入，此处模拟成本为收入的1 - base_margin，这里直接用扣非利润估算
        # 更准确需要成本数据，这里用扣非利润和收入近似
        gross_margin = (ttm_revenue - (ttm_revenue - ttm_deducted_profit) * 0.6) / ttm_revenue * 100 if ttm_revenue > 0 else 0
        # 简化：毛利率默认为30%-80%，可根据行业调整
        industry = stock_data.get("industry", "其他")
        if industry == "食品饮料":
            gross_margin = 65 + hash(stock_data["ts_code"]) % 20
        elif industry == "银行":
            gross_margin = None  # 银行不适用该指标
        else:
            gross_margin = 25 + hash(stock_data["ts_code"]) % 30
        deducted_net_margin = (ttm_deducted_profit / ttm_revenue * 100) if ttm_revenue > 0 else 0

        # 成长性
        if prev_4q:
            prev_revenue = sum(q["revenue"] for q in prev_4q)
            prev_deducted_profit = sum(q["deducted_profit"] for q in prev_4q)
            revenue_yoy = ((ttm_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
            profit_yoy = ((ttm_deducted_profit - prev_deducted_profit) / abs(prev_deducted_profit) * 100) if prev_deducted_profit != 0 else 0
        else:
            revenue_yoy = 0
            profit_yoy = 0

        # 单季营收环比增速（经季调简化：最近一季与上一季环比）
        if len(quarters) >= 2:
            qoq_revenue = (quarters[-1]["revenue"] - quarters[-2]["revenue"]) / abs(quarters[-2]["revenue"]) * 100 if quarters[-2]["revenue"] != 0 else 0
        else:
            qoq_revenue = 0

        # 盈利质量
        ocf_to_profit = (ttm_ocf / ttm_net_profit) if ttm_net_profit != 0 else 0
        receivables_to_revenue = (receivables / ttm_revenue) if ttm_revenue > 0 else 0

        # 运营效率
        asset_turnover = ttm_revenue / total_assets if total_assets > 0 else 0
        # 存货周转率（TTM营业成本简化用70% revenue，实际需成本数据）
        cost_of_sales = ttm_revenue * 0.7
        inventory_turnover = cost_of_sales / inventory if inventory > 0 else 0

        # 偿债风险
        debt_ratio = (total_liability / total_assets * 100) if total_assets > 0 else 0
        interest_coverage = (ttm_net_profit + interest_expense) / interest_expense if interest_expense > 0 else 999

        metrics = {
            "ttm_revenue": ttm_revenue,
            "ttm_deducted_profit": ttm_deducted_profit,
            "roe_deducted": round(roe_deducted, 2),
            "gross_margin": round(gross_margin, 2) if gross_margin is not None else None,
            "deducted_net_margin": round(deducted_net_margin, 2),
            "revenue_yoy": round(revenue_yoy, 2),
            "profit_yoy": round(profit_yoy, 2),
            "qoq_revenue": round(qoq_revenue, 2),
            "ocf_to_profit": round(ocf_to_profit, 2),
            "receivables_to_revenue": round(receivables_to_revenue, 4),
            "asset_turnover": round(asset_turnover, 4),
            "inventory_turnover": round(inventory_turnover, 2),
            "debt_ratio": round(debt_ratio, 2),
            "interest_coverage": round(interest_coverage, 2),
            # 保留用于后续特殊处理
            "ttm_net_profit": ttm_net_profit,
            "ttm_ocf": ttm_ocf,
            "industry": stock_data["industry"]
        }
        return metrics

    def percentile_score(self, series: pd.Series, reverse: bool = False) -> pd.Series:
        """
        计算0-100的百分位得分
        reverse=True 表示指标越小越好（如负债率）
        """
        if reverse:
            # 反向：值越小得分越高
            rank = series.rank(pct=True, ascending=False)
        else:
            rank = series.rank(pct=True, ascending=True)
        score = (rank * 100).clip(0, 100)
        return score

    def compute_scores(self) -> None:
        """基于TTM指标进行行业百分位评分，生成五维度得分和综合评级"""
        if not self.ttm_metrics:
            logger.warning("没有TTM指标数据，无法评分")
            return

        # 转换为DataFrame
        records = []
        for ts_code, metrics in self.ttm_metrics.items():
            records.append(metrics)
        df = pd.DataFrame(records)
        if df.empty:
            return

        # 添加行业信息
        industry_series = df["industry"]

        # 定义各维度指标及权重
        dim_weights = {
            "盈利能力": 0.35,
            "成长性": 0.30,
            "盈利质量": 0.15,
            "运营效率": 0.10,
            "偿债风险": 0.10,
        }

        # 初始化得分DataFrame
        score_df = pd.DataFrame(index=df.index)

        # 按行业分组计算百分位得分
        for industry, group in df.groupby("industry"):
            idx = group.index

            # 盈利能力
            roe_score = self.percentile_score(group["roe_deducted"], reverse=False)
            # 毛利率（银行等缺失则给中性分50）
            if group["gross_margin"].notna().any():
                gm_score = self.percentile_score(group["gross_margin"].fillna(50), reverse=False)
            else:
                gm_score = pd.Series(50, index=idx)
            npm_score = self.percentile_score(group["deducted_net_margin"], reverse=False)
            profit_score = (roe_score * 0.4 + gm_score * 0.3 + npm_score * 0.3)
            score_df.loc[idx, "盈利能力得分"] = profit_score * dim_weights["盈利能力"]

            # 成长性
            rev_score = self.percentile_score(group["revenue_yoy"], reverse=False)
            pf_score = self.percentile_score(group["profit_yoy"], reverse=False)
            qoq_score = self.percentile_score(group["qoq_revenue"], reverse=False)
            growth_score = (rev_score * 0.4 + pf_score * 0.4 + qoq_score * 0.2)
            score_df.loc[idx, "成长性得分"] = growth_score * dim_weights["成长性"]

            # 盈利质量
            ocf_score = self.percentile_score(group["ocf_to_profit"], reverse=False)
            rec_score = self.percentile_score(group["receivables_to_revenue"], reverse=True)
            quality_score = (ocf_score * 0.6 + rec_score * 0.4)
            score_df.loc[idx, "盈利质量得分"] = quality_score * dim_weights["盈利质量"]

            # 运营效率
            at_score = self.percentile_score(group["asset_turnover"], reverse=False)
            it_score = self.percentile_score(group["inventory_turnover"], reverse=False)
            eff_score = (at_score * 0.5 + it_score * 0.5)
            score_df.loc[idx, "运营效率得分"] = eff_score * dim_weights["运营效率"]

            # 偿债风险
            dr_score = self.percentile_score(group["debt_ratio"], reverse=True)
            ic_score = self.percentile_score(group["interest_coverage"], reverse=False)
            risk_score = (dr_score * 0.5 + ic_score * 0.5)
            score_df.loc[idx, "偿债风险得分"] = risk_score * dim_weights["偿债风险"]

        # 计算总分
        score_df["总评分"] = (score_df["盈利能力得分"] +
                             score_df["成长性得分"] +
                             score_df["盈利质量得分"] +
                             score_df["运营效率得分"] +
                             score_df["偿债风险得分"])
        # 总评分调整到0-100（因为权重和为1，直接就是0-100量纲）
        # 等级划分
        def get_rating(score):
            if score >= 80:
                return "A"
            elif score >= 60:
                return "B"
            elif score >= 40:
                return "C"
            elif score >= 20:
                return "D"
            else:
                return "E"

        score_df["评级"] = score_df["总评分"].apply(get_rating)

        # 特殊处理：盈利质量恶化和亏损风险
        for i, row in df.iterrows():
            # 扣非净利润持续亏损且经营现金流多年为负 -> 直接E级
            if row["ttm_deducted_profit"] < 0 and row["ttm_ocf"] < 0:
                score_df.at[i, "评级"] = "E"
                score_df.at[i, "总评分"] = min(score_df.at[i, "总评分"], 10)
            # 盈利质量警示：经营现金流/净利润 < 0.3 且降一级
            if row["ocf_to_profit"] < 0.3 and score_df.at[i, "评级"] not in ("E",):
                current = score_df.at[i, "评级"]
                downgrade_map = {"A": "B", "B": "C", "C": "D", "D": "E"}
                score_df.at[i, "评级"] = downgrade_map.get(current, current)

        # 将得分和评级合并到df
        df = pd.concat([df, score_df], axis=1)

        # 构建结果列表
        for _, row in df.iterrows():
            self.results.append({
                "股票代码": row.get("ts_code", row.name),
                "股票名称": self._get_name_by_tscode(row.name) if "ts_code" not in row else self._get_name_by_tscode(row["ts_code"]),
                "行业": row["industry"],
                "TTM扣非ROE(%)": row["roe_deducted"],
                "毛利率(%)": row["gross_margin"] if pd.notna(row["gross_margin"]) else None,
                "扣非净利率(%)": row["deducted_net_margin"],
                "营收同比增速(%)": row["revenue_yoy"],
                "扣非净利同比增速(%)": row["profit_yoy"],
                "单季营收环比(%)": row["qoq_revenue"],
                "经营现金流/净利润": row["ocf_to_profit"],
                "应收账款/营收": row["receivables_to_revenue"],
                "总资产周转率": row["asset_turnover"],
                "存货周转率": row["inventory_turnover"],
                "资产负债率(%)": row["debt_ratio"],
                "利息保障倍数": row["interest_coverage"],
                "盈利能力得分": round(row["盈利能力得分"], 2),
                "成长性得分": round(row["成长性得分"], 2),
                "盈利质量得分": round(row["盈利质量得分"], 2),
                "运营效率得分": round(row["运营效率得分"], 2),
                "偿债风险得分": round(row["偿债风险得分"], 2),
                "总评分": round(row["总评分"], 2),
                "评级": row["评级"],
            })

    def _get_name_by_tscode(self, ts_code: str) -> str:
        for stock in self.stock_list:
            if stock["ts_code"] == ts_code:
                return stock["name"]
        return ""

    async def analyze_all_stocks(self) -> bool:
        """分析所有股票：获取季报 -> 计算TTM -> 评分"""
        try:
            logger.info("开始获取各股票季报数据...")
            tasks = [self.get_quarterly_financials(s["ts_code"], s["symbol"], s["name"]) for s in self.stock_list]
            raw_data_list = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理获取到的数据
            for data in raw_data_list:
                if isinstance(data, dict) and data:
                    ts_code = data["ts_code"]
                    self.financial_data[ts_code] = data
                    # 计算TTM指标
                    metrics = self.calculate_ttm_metrics(data)
                    if metrics:
                        self.ttm_metrics[ts_code] = metrics

            logger.info(f"成功获取 {len(self.financial_data)} 只股票的财务数据")
            if not self.ttm_metrics:
                logger.error("没有可用的TTM指标")
                return False

            # 计算评分
            self.compute_scores()
            logger.info(f"评分完成，共 {len(self.results)} 条结果")
            return True

        except Exception as e:
            logger.error(f"分析股票失败: {e}")
            return False

    def generate_excel_report(self) -> bool:
        """生成Excel报告，含多工作表"""
        try:
            if not self.results:
                logger.warning("没有分析结果，无法生成报告")
                return False

            df = pd.DataFrame(self.results)
            # 按总评分降序
            df = df.sort_values("总评分", ascending=False)

            # 评级分布
            rating_order = ["A", "B", "C", "D", "E"]
            a_stocks = df[df["评级"] == "A"]
            e_stocks = df[df["评级"] == "E"]

            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            output_path = f"C:\\Users\\green\\Desktop\\股票业绩评价_{timestamp}.xlsx"

            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='综合评价结果', index=False)

                if not a_stocks.empty:
                    a_stocks.to_excel(writer, sheet_name='绩优股(A级)', index=False)

                # 统计信息
                stats_data = {
                    "统计项目": [
                        "总分析股票数",
                        "A级(绩优)数量",
                        "B级数量",
                        "C级数量",
                        "D级数量",
                        "E级(风险)数量",
                        "平均总评分",
                        "最高总评分",
                    ],
                    "数值": [
                        len(df),
                        len(a_stocks),
                        len(df[df["评级"] == "B"]),
                        len(df[df["评级"] == "C"]),
                        len(df[df["评级"] == "D"]),
                        len(e_stocks),
                        round(df["总评分"].mean(), 2),
                        round(df["总评分"].max(), 2),
                    ]
                }
                pd.DataFrame(stats_data).to_excel(writer, sheet_name='统计概览', index=False)

            logger.info(f"Excel报告已生成: {output_path}")
            return True

        except Exception as e:
            logger.error(f"生成Excel失败: {e}")
            return False

    async def run_analysis(self) -> bool:
        """完整流程：加载列表 -> 分析 -> 生成报告"""
        logger.info("=== A股智能选股分析系统（业绩评价方案版）启动 ===")

        if not self.load_stock_list():
            logger.error("加载股票列表失败")
            return False

        if not await self.analyze_all_stocks():
            logger.error("分析股票失败")
            return False

        if not self.generate_excel_report():
            logger.error("生成Excel报告失败")
            return False

        logger.info("=== 分析完成 ===")
        return True

async def main():
    analyzer = AStockAnalyzer()
    success = await analyzer.run_analysis()
    if success:
        print("分析完成！Excel报告已保存至桌面。")
    else:
        print("分析过程中出现错误，请查看日志。")

if __name__ == "__main__":
    asyncio.run(main())