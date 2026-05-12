"""
配置文件 - A股年报增长率分析项目
"""

import os

# 东方财富API配置
EASTMONEY_CONFIG = {
    'api_key': os.getenv('EASTMONEY_API_KEY', 'your_api_key_here'),
    'base_url': 'https://dcfm.eastmoney.com',
    'timeout': 30,
    'retry_times': 3
}

# 数据库配置
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'stock_analysis',
    'user': 'root',
    'password': 'your_password'
}

# 分析参数配置
ANALYSIS_CONFIG = {
    # 筛选条件
    'min_growth_rate': 0.5,  # 最小增长率50%
    'max_growth_rate': 10.0,  # 最大增长率1000%（避免异常值）
    
    # 时间范围
    'report_year': 2025,
    'quarter': '年报',  # 年报或季报
    
    # 财务指标
    'revenue_growth_field': '营业收入同比增长率',
    'profit_growth_field': '净利润同比增长率',
    'roe_growth_field': '净资产收益率同比增长率'
}

# 文件路径配置
PATHS = {
    'data_dir': './data',
    'output_dir': './output',
    'log_dir': './logs',
    'temp_dir': './temp'
}

# 创建必要的目录
for path in PATHS.values():
    if not os.path.exists(path):
        os.makedirs(path)