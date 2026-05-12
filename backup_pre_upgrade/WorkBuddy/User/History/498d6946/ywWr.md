# A股年报增长率分析项目

## 项目目标
分析2025年年报中增长率大于50%的A股股票，从东方财富金融工具集获取数据。

## 主要功能
- 批量获取股票代码和基本信息
- 提取2025年年度报告财务数据
- 计算同比增长率
- 筛选增长率大于50%的股票
- 生成分析报告和可视化图表

## 技术栈
- Python 3.13+
- 东方财富金融API
- Pandas数据处理
- Matplotlib/Seaborn可视化
- Jupyter Notebook分析环境

## 快速开始
1. 安装依赖: `pip install -r requirements.txt`
2. 配置API密钥
3. 运行主程序: `python main.py`
4. 查看分析结果: `jupyter notebook analysis.ipynb`

## 数据来源
- 东方财富金融工具集API
- A股市场股票代码列表
- 2025年年度报告财务数据