# 使用说明

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置API密钥
编辑 `config.py` 文件，设置您的东方财富API密钥：
```python
EASTMONEY_CONFIG = {
    'api_key': 'your_actual_api_key_here',
    # ... 其他配置
}
```

### 3. 运行分析程序
```bash
python main.py
```

### 4. 查看分析结果
打开 Jupyter Notebook：
```bash
jupyter notebook analysis.ipynb
```

## 项目结构

```
├── README.md              # 项目说明
├── config.py             # 配置文件
├── main.py               # 主程序
├── api_client.py         # API客户端
├── data_processor.py     # 数据处理模块
├── analysis.ipynb        # 数据分析笔记本
├── requirements.txt      # Python依赖
└── data/                 # 数据目录
    └── output/          # 输出结果
    └── logs/            # 日志文件
```

## 功能说明

### 数据获取
- 从东方财富API获取A股市场股票列表
- 批量获取2025年年度报告财务数据
- 支持多种财务指标：营业收入、净利润、ROE等

### 数据处理
- 自动清洗原始数据
- 计算同比增长率
- 筛选高增长股票（>50%增长率）

### 分析报告
- 生成Excel格式的分析报告
- 提供Jupyter Notebook进行深度分析
- 包含可视化图表和统计信息

## 自定义配置

### 修改筛选条件
在 `config.py` 中调整：
```python
ANALYSIS_CONFIG = {
    'min_growth_rate': 0.5,  # 最小增长率50%
    'max_growth_rate': 10.0, # 最大增长率限制
    'report_year': 2025,     # 报告年份
}
```

### 添加更多股票
修改 `main.py` 中的 `get_stock_codes()` 函数，添加更多股票代码。

## 常见问题

### Q: API调用频率限制怎么办？
A: 代码中已内置重试机制和请求间隔，建议根据实际API限制调整 `api_client.py` 中的 `time.sleep()` 参数。

### Q: 数据文件格式不对怎么办？
A: 检查 `data_processor.py` 中的数据清洗逻辑，确保字段名称与API返回的数据匹配。

### Q: 如何添加新的分析维度？
A: 在 `analysis.ipynb` 中添加新的分析单元格，使用Pandas和Matplotlib进行数据处理和可视化。

## 技术支持

如有问题，请检查：
1. 网络连接是否正常
2. API密钥是否正确配置
3. 日志文件 `logs/analysis.log` 中的错误信息

## 更新记录

- v1.0.0 (2024-04-24): 初始版本发布
  - 基础数据获取功能
  - 高增长股票筛选
  - 基本分析报告