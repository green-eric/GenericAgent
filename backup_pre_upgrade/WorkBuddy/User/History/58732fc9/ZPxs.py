"""
数据处理器 - 处理东方财富API返回的数据
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

class DataProcessor:
    """数据处理类，负责清洗和转换财务数据"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def clean_financial_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """
        清洗原始财务数据

        Args:
            raw_data: 从API获取的原始数据

        Returns:
            清洗后的DataFrame
        """
        try:
            # 复制数据避免修改原数据
            df = raw_data.copy()

            # 删除全为空的行
            df.dropna(how='all', inplace=True)

            # 处理数值列的空值
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # 填充合理的默认值
            growth_columns = [col for col in df.columns if '增长率' in col]
            for col in growth_columns:
                if col in df.columns:
                    df[col].fillna(0, inplace=True)  # 无增长率为0

            self.logger.info(f"数据清洗完成，剩余 {len(df)} 条记录")
            return df

        except Exception as e:
            self.logger.error(f"数据清洗失败: {str(e)}")
            raise

    def calculate_growth_rate(self,
                            current_value: float,
                            previous_value: float) -> float:
        """
        计算同比增长率

        Args:
            current_value: 当前期数值
            previous_value: 上期数值

        Returns:
            同比增长率（小数形式）
        """
        if previous_value == 0:
            return 0.0 if current_value == 0 else float('inf')

        growth_rate = (current_value - previous_value) / abs(previous_value)
        return growth_rate

    def filter_high_growth_stocks(self,
                                df: pd.DataFrame,
                                min_growth_rate: float = 0.5) -> pd.DataFrame:
        """
        筛选高增长股票

        Args:
            df: 包含财务数据的DataFrame
            min_growth_rate: 最小增长率阈值

        Returns:
            筛选后的高增长股票DataFrame
        """
        try:
            # 定义需要筛选的增长率字段
            growth_fields = [
                '营业收入同比增长率',
                '净利润同比增长率',
                '净资产收益率同比增长率'
            ]

            filtered_df = df.copy()

            # 应用筛选条件
            for field in growth_fields:
                if field in filtered_df.columns:
                    # 只保留增长率大于阈值的记录
                    filtered_df = filtered_df[
                        filtered_df[field] > min_growth_rate
                    ].copy()

            self.logger.info(f"筛选完成，找到 {len(filtered_df)} 只高增长股票")
            return filtered_df

        except Exception as e:
            self.logger.error(f"筛选高增长股票失败: {str(e)}")
            raise

    def export_analysis_results(self,
                              df: pd.DataFrame,
                              output_path: str,
                              file_format: str = 'xlsx'):
        """
        导出分析结果

        Args:
            df: 要导出的DataFrame
            output_path: 输出文件路径
            file_format: 文件格式 ('xlsx', 'csv', 'json')
        """
        try:
            if file_format == 'xlsx':
                with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='高增长股票', index=False)
                    # 添加统计摘要
                    summary_stats = df.describe()
                    summary_stats.to_excel(writer, sheet_name='统计摘要')

            elif file_format == 'csv':
                df.to_csv(output_path, index=False)

            elif file_format == 'json':
                df.to_json(output_path, orient='records', force_ascii=False)

            self.logger.info(f"结果已导出到: {output_path}")

        except Exception as e:
            self.logger.error(f"导出结果失败: {str(e)}")
            raise