## 用户需求分析

用户要求**移除现有逻辑**，基于附件（README.md + score_system.py）重新设计评分系统。

### 附件核心设计（目标状态）

**1. 数据源**：AkShare 三大报表接口（利润表、资产负债表、现金流量表），结构化DataFrame数据，非文本解析。

**2. 单季拆分规则**：

- Q1 = 一季报累计值
- Q2 = 中报累计值 - Q1累计值
- Q3 = 三季报累计值 - 中报累计值
- Q4 = 年报累计值 - 三季报累计值

**3. 核心指标（13+个）**：

- 成长类（单季同比）：单季归母净利润同比、单季营收同比、单季营业利润同比
- TTM盈利：ROE(摊薄)、毛利率、净利率
- TTM现金流：经营性现金流净额、自由现金流、净现比、自由现金流收益率、销售收现比
- 最新报表杠杆：D/E、权益乘数、资产负债率、流动比率、利息覆盖倍数
- 估值：PE-TTM

**4. 五维加权评分模型**：

| 维度 | 权重 | 子指标 |
| --- | --- | --- |
| 成长性 | 25% | 净利润同比(60%) + 营收同比(40%) |
| 盈利能力 | 30% | ROE(70%) + 毛利率(30%) |
| 现金流质量 | 20% | 净现比(40%) + 自由现金流收益率(30%) + 收现比(30%) |
| 偿债风险 | 15% | D/E(40%) + 流动比率(30%) + 资产负债率(30%) |
| 估值 | 10% | PE-TTM(100%) |


**5. 评分函数**：

- 正向线性：得分 = min(实际值/满分阈值, 1) × 100
- 反向线性：得分 = max(1 - 实际值/满分阈值, 0) × 100
- 总分 = Σ(各维度得分 × 权重)

**6. 满分阈值**：

- 净利润同比≥50%、营收同比≥30%、ROE≥15%、毛利率≥40%、净现比≥1.0、自由现金流收益率≥3%、D/E≤0.5、流动比率≥2.0、资产负债率≤50%、PE≤20

**7. 防未来函数**：仅使用 report_date ≤ eval_date 的财报数据，ST股票过滤

### 与现有系统的主要差异

| 对比项 | 现有(qa_scorer.py V7) | 目标(附件) |
| --- | --- | --- |
| 数据源 | NeoData API文本解析 | AkShare结构化接口 |
| 评分维度 | 4维(无估值) | 5维(含估值) |
| 子指标数 | 7个 | 13+个 |
| 评分方法 | 行业百分位排名 | 固定阈值线性得分 |
| 行业处理 | 申万一级行业相对排名 | 无行业区分 |
| 单季拆分 | 文本中直接提取同比 | 累计值做差后计算同比 |
| 自由现金流 | 未计算 | TTM经营现金流-TTM资本支出 |
| 收现比 | 未计算 | TTM销售收现/TTM营收 |
| 利息覆盖倍数 | 未计算 | (TTM营业利润+TTM财务费用)/TTM财务费用 |


### 需要保留的现有特性

- Excel报告输出（含评级着色、多工作表）
- 数据缓存机制（SQLite）
- 并发线程池
- ST股票过滤
- 日志系统
- 命令行参数接口

## 技术方案

### 架构设计

保留现有项目的整体架构框架（Config配置层、数据获取层、指标计算层、评分层、输出层），彻底替换内部实现逻辑。

```
┌─────────────────────────────────────────────────┐
│                  qa_scorer.py (重写)              │
├─────────────────────────────────────────────────┤
│ Config        │ 5维权重 + 10项阈值 + 重试配置     │
│ DataProvider  │ AkShare三大报表接口 + 行情接口    │
│ Calculator    │ 单季拆分 + TTM计算 + 杠杆计算     │
│ Scorer        │ 五维固定阈值线性评分              │
│ Reporter      │ Excel报告生成（保留现有输出格式）  │
│ main          │ 串联流程 + CLI参数                │
└─────────────────────────────────────────────────┘
```

### 模块划分

**1. Config类（重写）**

- 5维权重：growth=0.25, profitability=0.30, cash_flow=0.20, leverage=0.15, valuation=0.10
- 10项满分阈值：q_net_profit_yoy=0.5, q_revenue_yoy=0.3, roe_ttm=0.15, gross_margin_ttm=0.4, net_profit_ratio=1.0, fcf_yield=0.03, de_ratio_max=0.5, current_ratio_min=2.0, asset_liability_max=0.5, pe_max=20
- 保留：重试次数、超时、并发线程数、缓存天数

**2. DataProvider类（重写）**

- `get_combined_financials(symbol)`：调用akshare三大报表接口，按report_date内连接合并
- `get_stock_quote(symbol)`：获取总市值和PE-TTM
- 字段映射：营业总收入→revenue, 营业成本→oper_cost, 营业利润→oper_profit, 归母净利润→net_profit_parent, 财务费用→fin_expense, 资产总计→total_assets, 负债合计→total_liab, 股东权益合计→total_equity, 归母权益→equity_parent, 流动资产合计→current_assets, 流动负债合计→current_liab, 经营活动现金流量净额→ocf, 购建固定资产等支付的现金→capex, 销售商品提供劳务收到的现金→cash_from_sales

**3. IndicatorCalculator类（重写）**

- `_split_quarterly()`：累计值做差拆分为单季值
- `_calc_ttm_and_leverage()`：最近4季求和得TTM流量指标，最新报告期取存量指标
- 计算所有13+个输出指标

**4. Scorer类（重写）**

- 固定阈值线性得分（非百分位排名）
- 五维加权汇总
- PE≤0时估值得分为0

**5. 缓存层（保留+适配）**

- 保留SQLite缓存机制
- 修改表结构以适配新指标字段
- 缓存key使用纯股票代码（统一格式）

**6. 输出层（保留+扩展）**

- 保留Excel多工作表输出格式
- 新增列：营业利润同比、自由现金流、收现比、D/E、流动比率、PE-TTM

### 关键实现细节

**单季拆分核心逻辑**：

```python
# 报告期月份判断: 3=Q1, 6=Q2, 9=Q3, 12=Q4/Q
for i, row in df.iterrows():
    month = row['report_date'].month
    if month == 3:  # Q1
        q_value = row[col]
    else:
        prev_month = {6:3, 9:6, 12:9}[month]
        prev_row = df[(year==year) & (month==prev_month)]
        q_value = row[col] - prev_row[col] if prev_row exists else row[col]
```

**同比增速计算**：

```python
# 找去年同期报告期（精确到月）
last_year_date = current_date - pd.DateOffset(years=1)
yoy = (q_current / q_last_year - 1) * 100  # 百分比形式
```

**TTM计算**：

```python
recent4 = df.iloc[-4:]  # 最近4个报告期
ttm_recent4['q_xxx'].sum()  # 流量项目求和
latest = df.iloc[-1]  # 存量项目取最新
```

### 目录结构

```
QAScorer/
├── qa_scorer.py              # [重写] 主程序全部逻辑
├── README.md                 # [更新] 同步新设计文档
├── xuan.txt                  # [保留] 股票列表
├── industry_map_akshare.json # [保留] akshare行业缓存（可选扩展）
├── quarterly_cache.db        # [重建] 新结构缓存
└── requirements.txt          # [更新] akshare, pandas, numpy, openpyxl
```

### 依赖变更

- **移除**：requests（NeoData API不再需要）
- **保留新增**：akshare >= 1.12.0, pandas, numpy, openpyxl
- **保留**：sqlite3, logging, argparse, threading（标准库）

本任务为后端逻辑重写，不涉及UI/Excel界面设计变更。Excel报告输出格式保留现有样式（评级着色、多工作表布局），仅扩展列数以容纳新增指标。

## Agent Extensions

### Skill

- **Akshare Finance**: 用于验证AkShare接口调用的正确性，确认三大报表字段名称在不同akshare版本中的差异，以及获取实时行情数据的方式。
- 用途：在实现DataProvider层时，确认akshare接口的准确字段名和调用方式
- 预期产出：确保数据获取层接口调用正确，字段映射准确

- **xlsx**: 用于Excel报告生成阶段的格式设计和多工作表布局。
- 用途：生成包含评级着色、多工作表、新增指标列的Excel报告
- 预期产出：与现有输出格式一致但包含新增列的Excel报告