# A 股智能选股系统 V5.0.0

> 基于 NeoData 真实 API 数据，对 A 股年报进行结构化段落匹配与四维业绩评分。

---

## 快速开始

### 环境要求

- Python 3.10+
- 依赖：`requests`, `openpyxl`（`pip install requests openpyxl`）
- NeoData Token 放置于 `~/.workbuddy/.neodata_token`

### 基本用法

```bash
# 完整运行（默认 16 线程并发，读取 xuan.txt 股票列表）
python stock_analyzer.py

# 指定工作目录和股票列表
python stock_analyzer.py --base-dir ./data --stock-file my_stocks.txt

# 强制刷新缓存（忽略本地 SQLite 缓存）
python stock_analyzer.py --force-refresh

# 减少并发线程数
python stock_analyzer.py --workers 8

# 运行内置自测（验证段落提取与指标解析正确性）
python stock_analyzer.py --test
```

### 输出文件

运行结束后在工作目录生成：
- `股票业绩评价_{时间戳}.xlsx` — Excel 综合评价报告（多 Sheet）
- `股票分析数据_{时间戳}.json` — JSON 明细数据（按总分降序）

---

## 1. 版本概述

**V5 核心变更**（相对于 V4）：

| 变更项 | V4 | V5 |
|--------|----|----|
| 年报定位 | 正则切分 + 分类 | **直接段落匹配**（`"统计截止日期为YYYY1231的年报"` 锚点） |
| API 调用 | subprocess 调用 query.py 脚本 | **requests 直连** NeoData API |
| 网络层 | 每次新建连接 | **Session + HTTPAdapter 连接池**复用 |
| 查询语句 | 多关键词（利润表/现金流量表等） | 简化为 `{ts_code} {name} 年报` |
| 净利润提取 | 简单关键词匹配 | **排除衍生指标**（归母/扣非/现金含量/增长率/同比） |
| 自测模式 | 无 | **内置 `--test` 模式** |
| 遗留代码 | 含 subprocess/未使用配置项 | **全部清理** |

---

## 2. 整体流程

```
加载股票列表 → 缓存检查 → 并发获取 → 段落定位 → 逐行匹配 → 行业归类 → 评分计算 → 报告输出
```

| 步骤 | 说明 |
|------|------|
| **加载股票列表** | 从 `xuan.txt` 读取代码和名称，滤除北交所/科创板等不关注的板块（688/430/83/87 开头） |
| **缓存检查** | 对每只股票判断本地 SQLite 缓存中的年报是否过期 |
| **并发获取** | 使用 `requests.Session` 连接池，多线程并发调用 NeoData API |
| **段落定位** | 用 `"统计截止日期为YYYY1231的年报"` 精确锚定年报段落，跳过 Q1/Q3 等单季报 |
| **逐行匹配** | 在年报段落内按关键词逐行搜索，提取 13 个财务指标 |
| **行业归类** | 多级策略确定申万一级行业（文本解析 → 本地映射 → 名称规则 → API 补调 → 代码前缀） |
| **评分计算** | 基于年报指标，在同行业内进行百分位评分，生成四维评分和综合评级 |
| **报告输出** | 输出 Excel 综合评价报告、JSON 明细数据、异常日志 |

---

## 3. 数据获取与缓存

### 3.1 API 调用

直接通过 `requests` HTTP POST 调用 NeoData API：

```
POST https://copilot.tencent.com/agenttool/v1/neodata
Authorization: Bearer {token}
```

Token 从 `~/.workbuddy/.neodata_token` 文件读取。

### 3.2 查询构建

对每只股票发送精简查询：`{ts_code} {name} 年报`

> ⚠️ V5 刻意简化了查询语句。V4 曾使用"年报 主要财务指标 利润表 现金流量表 资产负债表"等多关键词，但实践中发现关键词过多反而导致 NeoData 搜索命中率下降。

API 返回一整段可能包含多年、多期报告的长文本（含 Q1、年报、Q4 等段落混合）。

### 3.3 缓存判断

缓存数据库中至少需要有一条 `annual` 类型的记录，否则直接刷新。

**年报过期条件**（满足任一即刷新）：
- 当前日期已超过 **年报年份 + 1 年** 的 **4 月 30 日**
- 距离报告日期的天数 > `CACHE_MAX_AGE_ANNUAL`（默认 **400 天**）

### 3.4 缓存读取

从数据库取出最新的 `annual` 记录，与 `stocks` 表中的名称、行业合并，组装成评分所需的字典结构。**不再涉及季报/半年报**。

---

## 4. 年报解析（V5 核心）

### 4.1 段落定位

**不再使用正则切分全文**，改为精确匹配锚点：

```python
统计截止日期为(\d{4})1231的年报
```

- 从锚点位置开始，到下一个 `"统计截止日期为"` 或文本结束为止
- Q1/Q3 等单季报被天然隔离

**兜底策略**：若未找到年报锚点，尝试从业绩趋势段落推断日期（`_guess_date_from_trend`），返回空指标。

### 4.2 指标提取

在定位到的年报段落内，按关键词逐行搜索，共提取 **13 个指标**：

| 类别 | 指标 | 关键词 | 提取方式 |
|------|------|--------|---------|
| **盈利能力** | ROE | 加权净资产收益率ROE / 净资产收益率ROE | 百分比 |
| | 毛利率 | 销售毛利率 | 百分比（从"毛利率"后取） |
| | 净利率 | 销售净利率 | 百分比（从"净利率"后取） |
| **成长性** | 营收同比 | 营业收入同比增长 / 营业总收入同比增长 | 同比增长率 |
| | 净利润同比 | 归母净利润同比增长 | 同比增长率 |
| **偿债风险** | 资产负债率 | 资产负债率 | 百分比 |
| **规模** | 营业总收入 | 营业总收入 / 营业收入 | 带单位数值 |
| | 净利润 | 净利润（特殊逻辑，见下方） | 带单位数值 |
| | 扣非净利润 | 扣非净利润 | 带单位数值 |
| | 经营现金流净额 | 经营活动产生的现金流量净额 | 带单位数值 |
| **现金流质量** | 经营现金流/净利润 | — | 计算值（OCF ÷ 净利润） |
| **运营效率** | 总资产周转率 | 总资产周转率 | 次数 |
| | 应收账款周转率 | 应收账款周转率 | 次数 |

> ⚠️ **净利润特殊逻辑**：找到以 `"净利润"` 开头但**不含** `"归母"`、`"扣非"`、`"现金含量"`、`"增长率"`、`"同比"` 的行，避免将衍生指标误识别为"净利润"。

---

## 5. 行业归属确定

按以下**优先级**依次尝试确定申万一级行业：

| 优先级 | 策略 | 说明 |
|--------|------|------|
| ① | 文本解析 | 从年报内容匹配"所属一级行业"等关键词 |
| ② | 本地映射表 | 查询 `industry_map.json`（运行时加载）；内置 `_FALLBACK_INDUSTRY_MAP` 当前为空，需外部维护 |
| ③ | 二级→一级映射 | 通过 `SECONDARY_TO_PRIMARY` 表转换（当前为空，需外部补充或通过 API 获取） |
| ④ | 名称规则 | 通过 `NAME_KEYWORD_INDUSTRY` 从股票名称推断（~20 个关键词） |
| ⑤ | API 补调 | 调用 NeoData API 查询（分批 100 只，批间休眠 1s，15 线程） |
| ⑥ | 代码前缀 | 用 `CODE_PREFIX_INDUSTRY` 猜测（仅 4 条规则：60→银行, 00→房地产, 30→医药生物, 68→电子） |

所有分类结果写入数据库 `stocks` 表，下次可复用。

> 💡 **优化建议**：若需提升行业分类覆盖率，可补充 `industry_map.json` 或填充 `SECONDARY_TO_PRIMARY` 映射表。

---

## 6. 评分体系

### 6.1 指标维度与权重

| 维度 | 权重 | 子指标及权重 |
|------|------|-------------|
| **盈利能力** | 35% | ROE（40%）、毛利率（30%）、净利率（30%） |
| **成长性** | 30% | 营收同比（40%）、净利润同比（60%） |
| **现金流质量** | 15% | 经营现金流/净利润 |
| **偿债风险** | 20% | 资产负债率 |

### 6.2 评分方法

- 每项指标在同行业内进行百分位排名，转化为 **0~100** 分值
- 行业样本不足 **5** 只时，退化为全市场百分位 × **0.95** 折扣
- ROE 为负值直接给 **0** 分
- 净利润与经营现金流均为负时，总分上限锁定为 **15** 分

### 6.3 完整度惩罚

统计 7 项核心指标（ROE、毛利率、净利率、营收同比、净利润同比、OCF/净利润、资产负债率）的非空数量：

| 完整度 | 条件 | 惩罚 |
|--------|------|------|
| 高 | ≥ 6/7 (85.7%) | 无 |
| 中 | = 4/7 (57.1%) | 无 |
| 低 | < 57.1% | 总分 × 0.9 |
| 极低 | ≤ 1 项 | 总分 × 0.9 × 0.75 |

### 6.4 评级与置信度

| 总分 | 评级 |
|------|------|
| ≥ 75 | **A** |
| ≥ 55 | **B** |
| ≥ 40 | **C** |
| ≥ 25 | **D** |
| < 25 | **E** |

**置信度** = 完整度等级（高 / 中 / 低）

---

## 7. 数据库结构

### `stocks` 表

| 字段 | 类型 | 说明 |
|------|------|------|
| `ts_code` | PK | 股票代码（如 000001.SZ） |
| `name` | | 股票名称 |
| `industry_l1` | | 申万一级行业 |
| `industry_l2` | | 申万二级行业 |
| `last_industry_update` | | 行业最后更新时间 |
| `last_full_update` | | 完整数据最后更新时间 |

### `financial_reports` 表

| 字段 | 说明 |
|------|------|
| `ts_code` | 股票代码 |
| `report_date` | 报告日期（如 20241231） |
| `report_type` | 报告类型（实际只使用 `annual`） |
| `roe`, `gross_margin`, `net_margin` | 盈利能力指标 |
| `revenue_yoy`, `profit_yoy` | 成长性指标 |
| `debt_ratio` | 偿债风险指标 |
| `net_profit`, `deducted_profit`, `revenue` | 规模指标 |
| `ocf_to_profit`, `ocf_abs` | 现金流指标 |
| `asset_turnover`, `ar_turnover` | 运营效率指标 |
| `fetch_success` | 获取是否成功（1/0） |
| `last_update` | 最后更新时间 |

> **唯一约束**：`(ts_code, report_date, report_type)`

---

## 8. 并发与限流

### 8.1 并发架构

- `ThreadPoolExecutor`（默认 **16 线程**）并发获取财务数据
- 共享 `requests.Session` + `HTTPAdapter` 连接池（`pool_connections` = `pool_maxsize` = workers）
- HTTPAdapter 内置重试（财务数据获取 `max_retries=2`，行业补调 `max_retries=1`）

### 8.2 限流保护

- **连续 API 错误**达到 **10** 次时，暂停 **20 秒**后重置计数器
- **正常但无数据**（新股/退市等）不计入连续错误
- 全局超时（`GLOBAL_TIMEOUT` = **7200s**）后取消剩余任务

### 8.3 行业补调分批

- 每批最多 **100** 只，批间休眠 **1s**
- **15 线程** + `requests.Session` 连接池（`max_retries=1`）
- 单只超时上限 **60s**，API 失败后降级为名称推断

### 8.4 进度日志

每处理 **100** 只股票输出一次进度：已处理数 / 总数、当前速率（只/秒）、已用时间 / 预估剩余时间、API 错误计数。

---

## 9. 自测模式

运行 `python stock_analyzer.py --test` 启动内置自测：

- 使用模拟 NeoData 返回格式（含 Q1 + 年报 + Q4 三段混合）
- 验证 `_extract_annual_block()` 正确排除 Q1/Q4，只提取年报段落
- 验证所有 13 个指标解析正确
- **关键验证**：净利润必须从 `"净利润1642130865.33元"` 提取，而非 `"净利润现金含量160.44%"`

---

## 10. 输出文件与字段说明

### Excel 报告：`股票业绩评价_{时间戳}.xlsx`

| Sheet | 内容 |
|-------|------|
| 综合评价结果 | 全部股票的四维评分、评级、年报日期（按总分降序） |
| A/B/C/D/E级股票 | 按评级分组的股票列表（共 5 个 Sheet） |
| 低置信度股票 | 完整度为"低"或"极低"的股票 |
| 获取失败股票 | API 未返回有效年报数据的股票 |
| 统计概览 | 总股票数、评级分布、成功/失败计数 |

> 共 8 个 Sheet：综合评价结果 + 5 个评级分组 + 低置信度 + 获取失败 + 统计概览。

### JSON 数据：`股票分析数据_{时间戳}.json`

```json
{
  "data_timestamp": "20260424_2331",
  "total_stocks": 435,
  "stocks": [ ... ]
}
```

### 输出字段一览

**财务指标（13个）**：`roe`、`gross_margin`、`net_margin`、`revenue_yoy`、`profit_yoy`、`debt_ratio`、`net_profit`、`deducted_profit`、`ocf_abs`、`ocf_to_profit`、`asset_turnover`、`ar_turnover`、`revenue`

**评分字段（5个）**：`total_score`、`profit_score`、`growth_score`、`ocf_score`、`debt_score`

**评级与元数据（8个）**：`grade`、`confidence`、`completeness`、`completeness_level`、`annual_report_date`、`market_fallback`、`fetch_success`、`ts_code`/`name`/`industry_l1`

---

## 11. 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--base-dir` | 工作目录 | 脚本所在目录 |
| `--stock-file` | 股票列表文件名 | `xuan.txt` |
| `--workers` | 并发线程数 | 16 |
| `--force-refresh` | 忽略缓存全量更新 | False |
| `--no-industry-patch` | 禁用行业 API 补调 | False |
| `--timeout` | 全局超时秒数（0=不限） | 7200 |
| `--test` | 运行内置自测并退出 | False |

---

## 12. 配置项速查

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `FINANCE_WORKERS` | 16 | 财务数据并发线程数 |
| `API_RETRY_TIMES` | 2 | 额外重试次数（总尝试次数 = 此值 + 1，默认共 3 次） |
| `API_RETRY_BACKOFF_BASE` | 3.0 | 指数退避基数 |
| `API_TIMEOUT` | 50 | 单次 API 调用超时（秒） |
| `GLOBAL_TIMEOUT` | 7200 | 全局超时（秒） |
| `PAUSE_CONSECUTIVE_EMPTY` | 10 | 连续 API 错误触发暂停的阈值 |
| `PAUSE_DURATION` | 20 | 暂停时长（秒） |
| `MIN_INDUSTRY_SAMPLES` | 5 | 行业评分最少样本数 |
| `CACHE_MAX_AGE_ANNUAL` | 400 | 年报缓存最大天数 |
| `NEGATIVE_PROFIT_PENALTY` | 15.0 | 净利润+现金流双负时的总分上限 |
| `MARKET_FALLBACK_DISCOUNT` | 0.95 | 全市场基准折扣 |
| `LOW_COMPLETENESS_PENALTY` | 0.9 | 低完整度惩罚系数 |
| `ULTRA_LOW_COMPLETENESS_PENALTY` | 0.75 | 极低完整度额外惩罚系数 |
| `INDUSTRY_API_WORKERS` | 15 | 行业补调并发线程数 |
| `INDUSTRY_CACHE_DAYS` | 365 | 行业映射缓存天数 |

---

## 13. 注意事项

> ⚠️ 系统严格依赖年报数据，若某股票未披露任何年报，将直接评为低完整度、低分，需人工关注。

> 📅 年报过期判断中的 **4 月 30 日**截止日可根据市场实际情况调整（`ANNUAL_DISCLOSURE_DEADLINE_MONTH=4` / `ANNUAL_DISCLOSURE_DEADLINE_DAY=30`）。

> 📊 行业内评分要求至少 **5** 只股票，小行业可能触发全市场基准，评分可能偏低。

> 🔧 NeoData Token 需放置在 `~/.workbuddy/.neodata_token` 文件中。

> 🔧 V5 查询语句已简化为 `{ts_code} {name} 年报`。如需调整查询策略，修改 `fetch_stock_finance()` 中的 `query` 变量。

---

*文档生成时间：2026-04-26*
*适用版本：V5.0.0*
*相关文档：[系统概览](../ANNUAL_QUARTERLY_OVERVIEW.md)*
