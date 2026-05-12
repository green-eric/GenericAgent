"""
主程序 - A股年报增长率分析

功能：
1. 获取A股市场股票列表
2. 批量获取2025年年度报告财务数据
3. 计算同比增长率
4. 筛选增长率大于50%的股票
5. 生成分析报告
"""

import logging
import pandas as pd
from typing import List, Dict
from api_client import EastMoneyAPIClient
from data_processor import DataProcessor
from report_analyzer import ReportAnalyzer
from growth_filter import AdvancedGrowthFilter, FilterCriteria
from config import ANALYSIS_CONFIG, PATHS
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(PATHS['log_dir'], 'analysis.log')),
        logging.StreamHandler()
    ]
)

class StockAnalysisApp:
    """A股年报增长率分析应用程序"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_simulated_data(self, stock_codes: List[str]) -> List[Dict]:
        """
        生成模拟财务数据（用于演示）

        Args:
            stock_codes: 股票代码列表

        Returns:
            模拟财务数据列表
        """
        import random
        from datetime import datetime

        simulated_data = []
        industries = ['科技', '金融', '消费', '医药', '新能源', '制造业', '房地产', '能源']

        self.logger.info(f"正在为 {len(stock_codes)} 只股票生成模拟数据...")

        for i, code in enumerate(stock_codes):
            # 随机选择行业
            industry = random.choice(industries)

            # 生成随机的增长率（模拟真实市场情况）
            base_revenue_growth = random.uniform(-0.2, 2.0)  # -20% 到 200%
            base_profit_growth = random.uniform(-0.3, 1.8)   # -30% 到 180%
            base_roe_growth = random.uniform(-0.5, 1.5)     # -50% 到 150%

            # 根据行业调整增长潜力
            if industry == '科技':
                base_revenue_growth *= 1.5
                base_profit_growth *= 1.3
            elif industry == '金融':
                base_revenue_growth *= 0.8
                base_profit_growth *= 0.9
            elif industry == '新能源':
                base_revenue_growth *= 1.8
                base_profit_growth *= 1.6

            # 确保数值合理
            revenue_growth = max(-0.5, min(5.0, base_revenue_growth))  # -50% 到 500%
            profit_growth = max(-0.5, min(5.0, base_profit_growth))     # -50% 到 500%
            roe_growth = max(-0.8, min(3.0, base_roe_growth))           # -80% 到 300%

            # 生成股票名称
            stock_name = f"模拟股票{i+1}"

            # 创建记录
            record = {
                'stock_code': code,
                'stock_name': stock_name,
                '所属行业': industry,
                '营业收入同比增长率': round(revenue_growth * 100, 2),
                '净利润同比增长率': round(profit_growth * 100, 2),
                '净资产收益率同比增长率': round(roe_growth * 100, 2),
                '毛利率同比增长率': round(random.uniform(-20, 100), 2),
                '总资产同比增长率': round(random.uniform(-10, 150), 2),
                '报告年份': 2025,
                '报告类型': '年报',
                '数据采集时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            simulated_data.append(record)

            # 每处理10只股票输出一次进度
            if (i + 1) % 10 == 0:
                self.logger.info(f"已生成 {i+1}/{len(stock_codes)} 只股票的模拟数据")

        self.logger.info("模拟数据生成完成")
        return simulated_data

    def get_stock_codes(self) -> List[str]:
        """
        获取A股市场股票代码列表
        这里使用示例数据，实际应用中应该从API获取
        """
        # 示例：前50只A股股票代码
        sample_codes = [
            '000001', '000002', '000008', '000063', '000069',
            '000100', '000157', '000166', '000333', '000408',
            '000538', '000568', '000625', '000651', '000725',
            '000776', '000783', '000858', '000876', '000895',
            '000936', '000961', '000983', '001979', '002001',
            '002007', '002008', '002027', '002032', '002044',
            '002120', '002127', '002142', '002153', '002174',
            '002202', '002230', '002236', '002252', '002271',
            '002304', '002352', '002410', '002415', '002456',
            '002460', '002466', '002475', '002508', '002558'
        ]
        return sample_codes

    def run_analysis(self):
        """运行完整的分析流程"""
        logger = logging.getLogger(__name__)
        logger.info("开始A股年报增长率分析项目")

        try:
            # 初始化组件
            api_client = EastMoneyAPIClient()
            processor = DataProcessor()

            # 获取股票列表
            logger.info("正在获取A股市场股票列表...")
            stock_codes = self.get_stock_codes()
            logger.info(f"获取到 {len(stock_codes)} 只股票")

            # 创建高级筛选器
            filter_criteria = FilterCriteria(
                min_revenue_growth=ANALYSIS_CONFIG['min_growth_rate'],
                min_profit_growth=ANALYSIS_CONFIG['min_growth_rate'] * 0.8,  # 利润增长稍低
                min_roe_growth=0.2,
                max_decline_threshold=-0.3
            )
            advanced_filter = AdvancedGrowthFilter(filter_criteria)

            # 创建报告分析器
            analyzer = ReportAnalyzer()

            # 模拟数据生成（实际项目中应从API获取）
            logger.info("正在生成模拟财务数据用于演示...")
            simulated_data = self.generate_simulated_data(stock_codes)
            df = pd.DataFrame(simulated_data)

            # 数据清洗
            logger.info("正在进行数据清洗...")
            cleaned_df = processor.clean_financial_data(df)

            # 计算关键指标
            logger.info("正在计算关键财务指标...")
            enhanced_df = analyzer.calculate_key_metrics(cleaned_df)

            # 高级筛选
            logger.info("正在进行高级增长率筛选...")
            filtered_df = advanced_filter.apply_multi_criteria_filter(enhanced_df)

            # 识别逆向投资机会
            contrarian_opportunities = advanced_filter.identify_contrarian_opportunities(enhanced_df)

            # 保存结果
            output_path = os.path.join(PATHS['output_dir'], f'high_growth_stocks_{ANALYSIS_CONFIG["report_year"]}.xlsx')
            processor.export_analysis_results(filtered_df, output_path)

            # 生成综合分析报告
            logger.info("正在生成综合分析报告...")
            report = analyzer.generate_comprehensive_report(
                enhanced_df,
                output_path=os.path.join(PATHS['output_dir'], 'comprehensive_analysis_report.txt')
            )

            # 创建可视化图表
            logger.info("正在创建可视化图表...")
            analyzer.create_visualizations(enhanced_df, PATHS['output_dir'])

            # 生成高级筛选报告
            filter_report = advanced_filter.generate_filter_report(
                enhanced_df,
                filtered_df,
                os.path.join(PATHS['output_dir'], 'advanced_filter_report.txt')
            )

            # 输出统计信息
            logger.info("=" * 50)
            logger.info("分析完成！")
            logger.info(f"总股票数量: {len(enhanced_df)}")
            logger.info(f"高增长股票数量 (>50%): {len(filtered_df)}")
            logger.info(f"逆向投资机会: {len(contrarian_opportunities)}")
            logger.info(f"结果已保存到: {output_path}")
            logger.info(f"综合分析报告: {report.get('file_path', 'N/A')}")
            logger.info(f"高级筛选报告: {filter_report.get('file_path', 'N/A')}")

            if len(filtered_df) > 0:
                logger.info("\n高增长股票Top 5:")
                for _, row in filtered_df.head().iterrows():
                    logger.info(f"{row.get('stock_code', '')} ({row.get('stock_name', '')}) "
                               f"- 营收:{row.get('营业收入同比增长率', 0):.1f}% "
                               f"- 利润:{row.get('净利润同比增长率', 0):.1f}%")

            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"程序执行出错: {str(e)}")
            raise

def main():
    """主函数"""
    app = StockAnalysisApp()
    app.run_analysis()

if __name__ == "__main__":
    main()