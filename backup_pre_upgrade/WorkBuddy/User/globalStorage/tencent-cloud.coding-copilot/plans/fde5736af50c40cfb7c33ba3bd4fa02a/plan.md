## 用户需求

在现有年报评分系统基础上，新增季度报告评分功能，最终输出**年报A级 ∩ 季报A级**的交集作为优选股票。

### 核心目标

- 对最新季度报告数据进行业绩评分（与年报评分逻辑一致）
- 取年报A级和季报A级的**交集**作为优选股票
- 单独展示"仅年报A"和"仅季报A"的股票
- 输出格式与年报一致

### 已确认的技术决策

1. **季度数据方案**：季度数据 + 年报补充字段

- 季度提供：毛利率、净利率、营收同比、净利润同比
- 年报补充：ROE、资产负债率、经营现金流/净利润

2. **行业评分基准**：沿用全市场年报基准（样本量充足）
3. **输出要求**：交集单独sheet + 仅年报A/仅季报A分别展示

### 季度报告字段覆盖（已实测）

| 字段 | 年报 | Q1 | Q3 | Q4 |
| --- | --- | --- | --- | --- |
| ROE | ✅ | ❌ | ❌ | ❌ |
| 毛利率 | ✅ | ✅ | ✅ | ✅ |
| 净利率 | ✅ | ✅ | ✅ | ✅ |
| 营收同比 | ✅ | ❌ | ✅ | ✅ |
| 净利润同比 | ✅ | ✅ | ✅ | ✅ |
| 资产负债率 | ✅ | ❌ | ❌ | ❌ |
| 经营现金流 | ✅ | ❌ | ❌ | ❌ |


### 现有代码状态

- stock_analyzer.py 已存在于 workplace/（V5.0.0，约1304行）
- 数据库 stock_cache.db 只有 annual 类型记录
- 评分门槛（MIN_INDICATORS_FOR_SCORING=4）已添加但尚未测试

## 技术方案

### 架构设计

```
当前流程: 加载股票 → 获取年报 → 解析年报 → 行业归类 → 年报评分 → 输出
新增流程: 获取季报 → 解析季报 → 合并年报补充字段 → 季报评分 → 交集计算 → 输出
```

### 核心改动模块

**1. 季度段落提取（新增函数）**

- `_extract_quarterly_block()`: 从API返回文本中提取最新季度段落
- 锚点格式: `统计截止日期为YYYYMMDD的Q1单季报/Q3单季报/Q4单季报`
- 取日期最新的季度（排除年报）

**2. 季度数据解析（复用+适配）**

- `parse_quarterly_financial()`: 复用 `parse_financial_all()` 的逐行匹配逻辑
- 返回季度可用的指标子集

**3. 季度评分（新增函数）**

- `calc_quarterly_score()`: 
- 输入：季度指标 + 年报补充指标
- 行业百分位基准：沿用年报行业基准（build_industry_stats）
- 权重与年报一致：盈利35% + 成长30% + 现金流15% + 偿债20%

**4. 报告生成（修改）**

- 新增 sheet：季报A级、年报A∩季报A、仅年报A、仅季报A
- 新增列：数据来源（年报/季报）、季度报告日期

**5. 数据库（修改）**

- financial_reports 表新增 report_type='quarterly' 记录
- 缓存季度数据

### 目录结构

```
workplace/
├── stock_analyzer.py          # [MODIFY] 主程序，新增季度评分逻辑
├── industry_map.json          # [UNCHANGED] 行业映射
├── stock_cache.db             # [AUTO-UPDATE] 新增季度数据缓存
├── xuan.txt                   # [UNCHANGED] 股票列表
└── README.md                  # [MODIFY] 更新文档说明季度评分
```

### 关键代码结构

```python
# 新增配置
class Config:
    CACHE_MAX_AGE_QUARTERLY = 90   # 季度缓存90天

# 新增函数
def _extract_quarterly_block(content: str) -> tuple:
    """提取最新季度段落，返回 (block_text, report_date, report_type)"""
    # 匹配 Q1单季报/Q3单季报/Q4单季报/中报
    # 取日期最新的

def parse_quarterly_financial(block: str) -> dict:
    """解析季度财务数据，返回可用指标"""

def calc_quarterly_score(stock, annual_supplement, industry_stats, fallback):
    """季度评分：季度指标 + 年报补充指标"""

# 修改主流程
def main():
    # ... 年报流程不变 ...
    # 新增：季度评分流程
    quarterly_results = compute_quarterly_scores(all_results)
    # 新增：交集计算
    preferred = annual_a & quarterly_a
    # 修改：报告生成
    generate_report_v2(annual_results, quarterly_results, preferred)
```

本任务为纯逻辑层修改，不涉及UI/UX设计变更。输出为Excel报告文件，通过新增Sheet页展示季度评分和交集结果。

## Agent Extensions

### Skill

- **NeoData金融搜索服务**
- 用途：验证季度报告API返回格式和字段覆盖情况
- 预期 outcome：确认季度段落锚点格式和可用字段

### SubAgent

- **code-explorer**
- 用途：探索 stock_analyzer.py 的完整代码结构，定位修改点
- 预期 outcome：确定函数插入位置和依赖关系