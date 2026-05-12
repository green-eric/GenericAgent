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

def setup_logging():
    """设置日志配置"""
    logger = logging.getLogger(__name__)
    return logger

def get_stock_codes() -> List[str]:
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

def main():
    """主函数"""
    logger = setup_logging()
    logger.info("开始A股年报增长率分析项目")

    try:
        # 初始化组件
        api_client = EastMoneyAPIClient()
        processor = DataProcessor()

        # 获取股票列表
        logger.info("正在获取A股市场股票列表...")
        stock_codes = get_stock_codes()
        logger.info(f"获取到 {len(stock_codes)} 只股票")

        # 批量获取财务数据
        logger.info("正在批量获取2025年财务报告...")
        financial_data = api_client.batch_get_financial_data(
            stock_codes,
            report_year=ANALYSIS_CONFIG['report_year']
        )

        if not financial_data:
            logger.error("未能获取任何财务数据")
            return

        # 转换为DataFrame
        df = pd.DataFrame(financial_data)
        logger.info(f"成功获取 {len(df)} 只股票的财务数据")

        # 数据清洗
        logger.info("正在进行数据清洗...")
        cleaned_df = processor.clean_financial_data(df)

        # 筛选高增长股票
        logger.info("正在筛选增长率大于50%的股票...")
        min_growth_rate = ANALYSIS_CONFIG['min_growth_rate']
        high_growth_stocks = processor.filter_high_growth_stocks(
            cleaned_df,
            min_growth_rate=min_growth_rate
        )

        # 保存结果
        output_path = os.path.join(PATHS['output_dir'], f'high_growth_stocks_{ANALYSIS_CONFIG["report_year"]}.xlsx')
        processor.export_analysis_results(high_growth_stocks, output_path)

        # 输出统计信息
        logger.info("=" * 50)
        logger.info("分析完成！")
        logger.info(f"总股票数量: {len(cleaned_df)}")
        logger.info(f"高增长股票数量 (>50%): {len(high_growth_stocks)}")
        logger.info(f"结果已保存到: {output_path}")

        if len(high_growth_stocks) > 0:
            logger.info("\n高增长股票列表:")
            for _, row in high_growth_stocks.head(10).iterrows():
                logger.info(f"{row.get('stock_code', '')} ({row.get('stock_name', '')})")

        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")
        raise

if __name__ == "__main__":
    main()