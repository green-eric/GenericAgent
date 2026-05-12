"""
年报分析器 - 专门用于处理2025年年报数据

功能：
- 从东方财富获取2025年年度报告
- 计算关键财务指标增长率
- 识别高增长潜力股票
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

class ReportAnalyzer:
    """年报分析器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.growth_threshold = 0.5  # 50%增长率阈值

    def load_financial_data(self, file_path: str) -> pd.DataFrame:
        """
        加载财务数据

        Args:
            file_path: 数据文件路径

        Returns:
            财务数据DataFrame
        """
        try:
            if file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_path}")

            self.logger.info(f"成功加载数据，共 {len(df)} 条记录")
            return df

        except Exception as e:
            self.logger.error(f"加载数据失败: {str(e)}")
            raise

    def calculate_key_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算关键财务指标

        Args:
            df: 原始财务数据

        Returns:
            包含关键指标的DataFrame
        """
        try:
            # 复制数据避免修改原数据
            result_df = df.copy()

            # 定义需要计算的增长率字段
            growth_fields_mapping = {
                '营业收入同比增长率': ['营业收入', '营业收入同比增长'],
                '净利润同比增长率': ['净利润', '净利润同比增长'],
                '毛利率同比增长率': ['毛利率', '毛利率同比增长'],
                '净资产收益率同比增长率': ['净资产收益率', '净资产收益率同比增长'],
                '总资产同比增长率': ['总资产', '总资产同比增长']
            }

            for new_col, (base_field, growth_field) in growth_fields_mapping.items():
                if base_field in result_df.columns and growth_field in result_df.columns:
                    # 过滤异常值（大于1000%）
                    mask = (result_df[growth_field] <= 1000) & (result_df[growth_field] >= -100)
                    result_df.loc[mask, new_col] = result_df.loc[mask, growth_field]
                else:
                    # 如果字段不存在，创建空列
                    result_df[new_col] = np.nan

            self.logger.info("关键指标计算完成")
            return result_df

        except Exception as e:
            self.logger.error(f"计算关键指标失败: {str(e)}")
            raise

    def identify_high_growth_stocks(self,
                                  df: pd.DataFrame,
                                  min_revenue_growth: float = 0.5,
                                  min_profit_growth: float = 0.5) -> pd.DataFrame:
        """
        识别高增长股票

        Args:
            df: 财务数据
            min_revenue_growth: 最小营收增长率
            min_profit_growth: 最小利润增长率

        Returns:
            高增长股票列表
        """
        try:
            # 筛选条件
            high_growth_mask = (
                (df['营业收入同比增长率'] >= min_revenue_growth) &
                (df['净利润同比增长率'] >= min_profit_growth)
            )

            high_growth_stocks = df[high_growth_mask].copy()
            high_growth_stocks = high_growth_stocks.sort_values(
                by=['营业收入同比增长率', '净利润同比增长率'],
                ascending=False
            )

            self.logger.info(f"找到 {len(high_growth_stocks)} 只高增长股票")
            return high_growth_stocks

        except Exception as e:
            self.logger.error(f"识别高增长股票失败: {str(e)}")
            raise

    def analyze_industry_performance(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        分析行业表现

        Args:
            df: 财务数据

        Returns:
            行业表现统计
        """
        try:
            if '所属行业' not in df.columns:
                return pd.DataFrame()

            # 按行业分组计算平均增长率
            industry_stats = df.groupby('所属行业').agg({
                '营业收入同比增长率': ['mean', 'count'],
                '净利润同比增长率': ['mean', 'count'],
                '毛利率同比增长率': ['mean', 'count']
            }).round(2)

            # 重命名列
            industry_stats.columns = [
                '营收平均增长率', '营收股票数量',
                '利润平均增长率', '利润股票数量',
                '毛利率平均增长率', '毛利率股票数量'
            ]

            # 按营收增长率排序
            industry_stats = industry_stats.sort_values('营收平均增长率', ascending=False)

            return industry_stats

        except Exception as e:
            self.logger.error(f"分析行业表现失败: {str(e)}")
            raise

    def generate_comprehensive_report(self,
                                    df: pd.DataFrame,
                                    output_path: str = None) -> Dict:
        """
        生成综合分析报告

        Args:
            df: 财务数据
            output_path: 输出文件路径

        Returns:
            分析报告字典
        """
        try:
            report = {}

            # 基本统计信息
            report['total_stocks'] = len(df)
            report['avg_revenue_growth'] = df['营业收入同比增长率'].mean()
            report['avg_profit_growth'] = df['净利润同比增长率'].mean()

            # 高增长股票分析
            high_growth_stocks = self.identify_high_growth_stocks(df)
            report['high_growth_count'] = len(high_growth_stocks)
            report['top_10_revenue_growth'] = high_growth_stocks.head(10)[
                ['stock_code', 'stock_name', '营业收入同比增长率', '净利润同比增长率']
            ].to_dict('records')

            # 行业分析
            industry_analysis = self.analyze_industry_performance(df)
            report['industry_performance'] = industry_analysis.to_dict('records')

            # 保存报告到文件
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write("# A股2025年年报分析报告\n\n")
                    f.write(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                    f.write("## 总体概况\n")
                    f.write(f"- 总股票数量: {report['total_stocks']}\n")
                    f.write(f"- 平均营收增长率: {report['avg_revenue_growth']:.2f}%\n")
                    f.write(f"- 平均利润增长率: {report['avg_profit_growth']:.2f}%\n")
                    f.write(f"- 高增长股票数量 (>50%): {report['high_growth_count']}\n\n")

                    f.write("## 高增长股票Top 10\n")
                    f.write("| 股票代码 | 股票名称 | 营收增长率 | 利润增长率 |\n")
                    f.write("|----------|----------|------------|------------|\n")
                    for stock in report['top_10_revenue_growth']:
                        f.write(f"| {stock['stock_code']} | {stock['stock_name']} | "
                               f"{stock['营业收入同比增长率']:.1f}% | {stock['净利润同比增长率']:.1f}% |\n")

                    f.write("\n## 行业表现排名\n")
                    for i, industry in enumerate(report['industry_performance'][:10], 1):
                        f.write(f"{i}. **{industry['所属行業']}**\n")
                        f.write(f"   - 平均营收增长: {industry['营业收入同比增长率_mean']:.1f}%\n")
                        f.write(f"   - 平均利润增长: {industry['净利润同比增长率_mean']:.1f}%\n")
                        f.write(f"   - 股票数量: {industry['营业收入同比增长率_count']}只\n\n")

            self.logger.info(f"综合分析报告已生成: {output_path}")
            return report

        except Exception as e:
            self.logger.error(f"生成报告失败: {str(e)}")
            raise

    def create_visualizations(self, df: pd.DataFrame, output_dir: str = './visualizations'):
        """
        创建可视化图表

        Args:
            df: 财务数据
            output_dir: 输出目录
        """
        try:
            import os
            os.makedirs(output_dir, exist_ok=True)

            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            sns.set_style("whitegrid")

            # 1. 增长率分布图
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('A股2025年年报财务指标分布', fontsize=16)

            # 营收增长率分布
            axes[0, 0].hist(df['营业收入同比增长率'].dropna(), bins=30, alpha=0.7, color='skyblue')
            axes[0, 0].set_title('营收增长率分布')
            axes[0, 0].set_xlabel('增长率 (%)')
            axes[0, 0].set_ylabel('股票数量')

            # 利润增长率分布
            axes[0, 1].hist(df['净利润同比增长率'].dropna(), bins=30, alpha=0.7, color='lightgreen')
            axes[0, 1].set_title('利润增长率分布')
            axes[0, 1].set_xlabel('增长率 (%)')
            axes[0, 1].set_ylabel('股票数量')

            # 相关性热力图
            correlation_cols = ['营业收入同比增长率', '净利润同比增长率', '毛利率同比增长率']
            correlation_matrix = df[correlation_cols].corr()

            sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0,
                       square=True, fmt='.2f', ax=axes[1, 0])
            axes[1, 0].set_title('财务指标相关性分析')

            # 高增长股票行业分布
            if '所属行业' in df.columns:
                high_growth = self.identify_high_growth_stocks(df)
                if len(high_growth) > 0 and '所属行业' in high_growth.columns:
                    industry_counts = high_growth['所属行业'].value_counts().head(10)
                    colors = plt.cm.Set3(np.linspace(0, 1, len(industry_counts)))
                    bars = axes[1, 1].barh(range(len(industry_counts)), industry_counts.values, color=colors)
                    axes[1, 1].set_yticks(range(len(industry_counts)))
                    axes[1, 1].set_yticklabels(industry_counts.index)
                    axes[1, 1].set_title('高增长股票行业分布 Top 10')
                    axes[1, 1].set_xlabel('股票数量')

            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'financial_analysis.png'), dpi=300, bbox_inches='tight')
            plt.close()

            self.logger.info(f"可视化图表已保存到: {output_dir}")

        except Exception as e:
            self.logger.error(f"创建可视化图表失败: {str(e)}")
            raise