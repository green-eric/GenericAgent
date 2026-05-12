"""
高级增长率筛选器 - 提供多维度增长率分析

功能：
- 多指标复合筛选
- 行业对比分析
- 趋势识别
- 风险调整后的增长评估
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

class GrowthType(Enum):
    """增长类型枚举"""
    HIGH_GROWTH = "高增长"      # >50%
    MODERATE_GROWTH = "中增长"   # 20%-50%
    STABLE_GROWTH = "稳定增长"   # 0%-20%
    DECLINE = "负增长"         # <0%

@dataclass
class FilterCriteria:
    """筛选条件数据类"""
    min_revenue_growth: float = 0.5
    min_profit_growth: float = 0.5
    min_roe_growth: float = 0.2
    max_decline_threshold: float = -0.3
    industry_top_percentile: float = 0.8
    trend_consistency: int = 3  # 连续几年增长

class AdvancedGrowthFilter:
    """高级增长率筛选器"""

    def __init__(self, criteria: FilterCriteria = None):
        self.criteria = criteria or FilterCriteria()
        self.logger = logging.getLogger(__name__)

    def classify_growth_type(self, growth_rate: float) -> GrowthType:
        """
        分类增长类型

        Args:
            growth_rate: 增长率（小数形式）

        Returns:
            增长类型
        """
        if growth_rate >= self.criteria.min_revenue_growth:
            return GrowthType.HIGH_GROWTH
        elif growth_rate >= 0.2:
            return GrowthType.MODERATE_GROWTH
        elif growth_rate >= 0:
            return GrowthType.STABLE_GROWTH
        else:
            return GrowthType.DECLINE

    def calculate_composite_score(self,
                                df: pd.DataFrame,
                                weights: Dict[str, float] = None) -> pd.Series:
        """
        计算综合评分

        Args:
            df: 财务数据
            weights: 各指标的权重

        Returns:
            综合评分Series
        """
        if weights is None:
            weights = {
                'revenue_growth': 0.4,
                'profit_growth': 0.4,
                'roe_growth': 0.2
            }

        try:
            # 标准化各指标（使用Z-score标准化）
            normalized_scores = {}

            for metric in ['营业收入同比增长率', '净利润同比增长率', '净资产收益率同比增长率']:
                if metric in df.columns:
                    # Z-score标准化
                    z_scores = (df[metric] - df[metric].mean()) / df[metric].std()
                    # 处理标准差为0的情况
                    if df[metric].std() == 0:
                        normalized_scores[metric] = 0
                    else:
                        normalized_scores[metric] = z_scores

            # 计算加权综合评分
            composite_score = (
                normalized_scores.get('营业收入同比增长率', 0) * weights['revenue_growth'] +
                normalized_scores.get('净利润同比增长率', 0) * weights['profit_growth'] +
                normalized_scores.get('净资产收益率同比增长率', 0) * weights['roe_growth']
            )

            return composite_score

        except Exception as e:
            self.logger.error(f"计算综合评分失败: {str(e)}")
            return pd.Series([0] * len(df), index=df.index)

    def apply_multi_criteria_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        应用多条件筛选

        Args:
            df: 财务数据

        Returns:
            筛选后的DataFrame
        """
        try:
            filtered_df = df.copy()

            # 基本筛选条件
            basic_mask = (
                (filtered_df['营业收入同比增长率'] >= self.criteria.min_revenue_growth) &
                (filtered_df['净利润同比增长率'] >= self.criteria.min_profit_growth) &
                (filtered_df['净资产收益率同比增长率'] >= self.criteria.min_roe_growth) &
                (filtered_df['营业收入同比增长率'] >= self.criteria.max_decline_threshold)
            )

            filtered_df = filtered_df[basic_mask]

            # 添加综合评分
            filtered_df['composite_score'] = self.calculate_composite_score(filtered_df)

            # 按综合评分排序
            filtered_df = filtered_df.sort_values('composite_score', ascending=False)

            self.logger.info(f"多条件筛选完成，剩余 {len(filtered_df)} 只股票")
            return filtered_df

        except Exception as e:
            self.logger.error(f"多条件筛选失败: {str(e)}")
            raise

    def analyze_industry_comparison(self, df: pd.DataFrame) -> Dict:
        """
        行业对比分析

        Args:
            df: 财务数据

        Returns:
            行业对比分析结果
        """
        try:
            if '所属行业' not in df.columns:
                return {}

            industry_analysis = {}

            for industry in df['所属行业'].unique():
                industry_data = df[df['所属行业'] == industry]

                analysis = {
                    'stock_count': len(industry_data),
                    'avg_revenue_growth': industry_data['营业收入同比增长率'].mean(),
                    'avg_profit_growth': industry_data['净利润同比增长率'].mean(),
                    'avg_roe_growth': industry_data['净资产收益率同比增长率'].mean(),
                    'high_growth_stocks': len(industry_data[
                        industry_data['营业收入同比增长率'] >= self.criteria.min_revenue_growth
                    ]),
                    'top_performer': industry_data.nlargest(1, '营业收入同比增长率').iloc[0]
                    if len(industry_data) > 0 else None
                }

                industry_analysis[industry] = analysis

            return industry_analysis

        except Exception as e:
            self.logger.error(f"行业对比分析失败: {str(e)}")
            raise

    def identify_contrarian_opportunities(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        识别逆向投资机会

        Args:
            df: 财务数据

        Returns:
            逆向投资机会列表
        """
        try:
            contrarian_df = df.copy()

            # 识别被低估的高增长股票
            # 条件：营收增长高但利润增长相对较低
            contrarian_mask = (
                (contrarian_df['营业收入同比增长率'] >= self.criteria.min_revenue_growth) &
                (contrarian_df['净利润同比增长率'] < self.criteria.min_profit_growth * 0.8) &
                (contrarian_df['营业收入同比增长率'] > contrarian_df['净利润同比增长率'] * 1.2)
            )

            contrarian_opportunities = contrarian_df[contrarian_mask].copy()
            contrarian_opportunities['opportunity_score'] = (
                contrarian_opportunities['营业收入同比增长率'] -
                contrarian_opportunities['净利润同比增长率']
            )

            contrarian_opportunities = contrarian_opportunities.sort_values(
                'opportunity_score', ascending=False
            )

            self.logger.info(f"找到 {len(contrarian_opportunities)} 个逆向投资机会")
            return contrarian_opportunities

        except Exception as e:
            self.logger.error(f"识别逆向投资机会失败: {str(e)}")
            raise

    def generate_filter_report(self,
                             original_df: pd.DataFrame,
                             filtered_df: pd.DataFrame,
                             output_path: str = None) -> Dict:
        """
        生成筛选报告

        Args:
            original_df: 原始数据
            filtered_df: 筛选后数据
            output_path: 输出文件路径

        Returns:
            筛选报告
        """
        try:
            report = {}

            # 筛选统计
            report['original_count'] = len(original_df)
            report['filtered_count'] = len(filtered_df)
            report['filter_ratio'] = len(filtered_df) / len(original_df) if len(original_df) > 0 else 0

            # 筛选前后对比
            if len(original_df) > 0:
                report['original_avg_metrics'] = {
                    'revenue_growth': original_df['营业收入同比增长率'].mean(),
                    'profit_growth': original_df['净利润同比增长率'].mean(),
                    'roe_growth': original_df['净资产收益率同比增长率'].mean()
                }

                if len(filtered_df) > 0:
                    report['filtered_avg_metrics'] = {
                        'revenue_growth': filtered_df['营业收入同比增长率'].mean(),
                        'profit_growth': filtered_df['净利润同比增长率'].mean(),
                        'roe_growth': filtered_df['净资产收益率同比增长率'].mean()
                    }

            # 行业分布变化
            industry_comparison = self.analyze_industry_comparison(filtered_df)
            report['industry_distribution'] = industry_comparison

            # 保存报告
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write("# A股增长率筛选分析报告\n\n")

                    f.write("## 筛选概况\n")
                    f.write(f"- 原始股票数量: {report['original_count']}\n")
                    f.write(f"- 筛选后股票数量: {report['filtered_count']}\n")
                    f.write(f"- 筛选比例: {report['filter_ratio']:.2%}\n\n")

                    if 'original_avg_metrics' in report and 'filtered_avg_metrics' in report:
                        f.write("## 指标对比\n")
                        f.write("| 指标 | 筛选前 | 筛选后 |\n")
                        f.write("|------|--------|--------|\n")
                        f.write(f"| 平均营收增长率 | {report['original_avg_metrics']['revenue_growth']:.2f}% | "
                               f"{report['filtered_avg_metrics']['revenue_growth']:.2f}% |\n")
                        f.write(f"| 平均利润增长率 | {report['original_avg_metrics']['profit_growth']:.2f}% | "
                               f"{report['filtered_avg_metrics']['profit_growth']:.2f}% |\n")
                        f.write(f"| 平均ROE增长率 | {report['original_avg_metrics']['roe_growth']:.2f}% | "
                               f"{report['filtered_avg_metrics']['roe_growth']:.2f}% |\n\n")

            self.logger.info(f"筛选报告已生成: {output_path}")
            return report

        except Exception as e:
            self.logger.error(f"生成筛选报告失败: {str(e)}")
            raise