# A股智能选股 / 业绩分析系统 V3.9.3 — 完整逻辑文档

## 1. 概述

本系统从指定股票列表出发，通过外部数据查询脚本获取最新年报/季报财务指标，基于行业或全市场进行百分位评分，生成综合评价结果（A~E级），并输出Excel报告及JSON数据。支持多线程并发获取、SQLite缓存、失败重试、行业自动补调等功能。

## 2. 系统架构与文件组织

- **主脚本**：`stock_analyzer.py`
- **工作目录**：默认为脚本所在目录，可通过 `--base-dir` 指定
- **外部依赖**：
  - `query.py`（环境变量 `NEODATA_QUERY_PATH` 指定路径，用于查询财务数据）
  - `pandas`、`openpyxl`（生成Excel报告）
- **数据文件**：
  - `xuan.txt` — 股票列表文件（每行 `代码 名称`，可包含注释）
  - `industry_map.json` — 完整行业映射表（可选，缺失时使用内置100条兜底表）
  - `stock_cache.db` — SQLite数据库，缓存股票信息和财务报告
- **输出文件**：
  - `股票业绩评价_<时间戳>.xlsx`
  - `股票分析数据_<时间戳>.json`
  - `日志文件 stock_analyzer_<时间戳>.log`

## 3. 配置中心（Config类）

集中管理所有可调参数，部分可通过命令行覆盖。

### 路径配置

| 参数 | 说明 |
|------|------|
| `BASE_DIR` | 脚本所在目录 |
| `QUERY_SCRIPT` | 外部数据查询脚本路径 |
| `DEFAULT_STOCK_FILE` | 股票列表文件路径 |
| `OUTPUT_DIR` | 输出目录 |
| `INDUSTRY_MAP_FILE` | 行业映射JSON文件路径 |
| `DB_FILE` | 缓存数据库路径 |

### 采集参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `FINANCE_WORKERS` | 8 | 并发线程数（可 `--workers` 调整） |
| `API_RETRY_TIMES` | 2 | API调用重试次数 |
| `API_RETRY_BACKOFF_BASE` | 3.0秒 | 重试退避基数 |
| `API_TIMEOUT` | 50 | API超时秒数 |
| `GLOBAL_DELAY` | — | 全局延时（未使用） |
| `PAUSE_CONSECUTIVE_EMPTY` | 5次 | 连续空结果暂停阈值 |
| `PAUSE_DURATION` | 30秒 | 暂停时长 |
| `GLOBAL_TIMEOUT` | 3600秒 | 全局超时（0不限） |

### 评分权重

```python
SCORE_WEIGHTS = {
    "profit": 0.35,
    "growth": 0.30,
    "ocf_quality": 0.15,
    "debt_risk": 0.20
}
PROFIT_SUB = {"roe": 0.4, "gross_margin": 0.3, "net_margin": 0.3}
GROWTH_SUB = {"revenue_yoy": 0.4, "profit_yoy": 0.6}
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `NEGATIVE_PROFIT_PENALTY` | 15.0 | 净利润与经营现金流同时为负时总分上限 |
| `MARKET_FALLBACK_DISCOUNT` | 0.95 | 使用全市场比较时的折扣 |
| `LOW_COMPLETENESS_PENALTY` | 0.9 | 数据完整度低时的折扣 |
| `COMPLETENESS_HIGH` | 0.7 | 完整度高阈值 |
| `COMPLETENESS_LOW` | 0.4 | 完整度低阈值 |

### 重试/补调控制

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `RETRY_FAILED_FINANCE` | True | 是否对获取失败股票重试 |
| `MAX_RETRY_FAILED_ITEMS` | 200 | 重试失败数量上限，避免无休止重试 |
| `RETRY_INDUSTRY_FOR_UNCLASSIFIED` | True | 是否对未分类股票调用行业API补调 |
| `INDUSTRY_API_WORKERS` | 3 | 行业补调并发数 |

### 缓存有效期

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CACHE_MAX_AGE_ANNUAL` | 400天 | 年报缓存最大天数 |
| `CACHE_MAX_AGE_QUARTERLY` | 100天 | 季报缓存最大天数 |

年报披露截止月/日：4月30日，在截止日前不强制更新上一年年报。

### 日志

`LOG_MAX_BYTES = 10MB`，备份数3，使用 `RotatingFileHandler`。

## 4. 日志与错误日志

- **初始化**：`setup_logging()` 创建日志对象，同时输出到文件和控制台。
- **全局错误日志** `error_log` 为 `list`，所有追加操作通过 `safe_error_append()` 加锁保护，确保多线程安全。
- 错误日志最终写入Excel的"异常日志"工作表。

## 5. 股票列表加载

函数：`load_stock_list(path)`

- 按UTF-8读取文件，忽略空行和 `#` 注释行。
- 每行格式：`代码 名称`，代码自动补齐6位（`zfill(6)`）。
- 过滤掉科创板、新三板等前缀（`688`、`430`、`83`、`87`）。
- 自动添加后缀：0或3开头 → `.SZ`，其余 → `.SH`，形成 `ts_code` 如 `000001.SZ`。

## 6. API调用（外部查询脚本）

函数：`run_neodata(query)`

- 构造命令：`[python, QUERY_SCRIPT, --query, query, --data-type, api]`
- 自带指数退避重试（最多 `API_RETRY_TIMES+1` 次）。
- 特殊处理：如果输出包含XML标记 `<Objs Version=`，提取其中JSON部分。
- 返回标准格式 `dict`，`code=="200"` 表示成功，否则返回错误信息。

## 7. 财务数据获取与解析

### 7.1 单股票获取：`fetch_stock_finance(ts_code, name)`

- 构造查询语句：`"{ts_code} {name} 年报 主要财务指标 利润表 现金流量表 资产负债表"`
- 调用 `run_neodata`，提取返回的 `apiRecall` 列表中所有 `content`，拼接为全文。
- 调用 `parse_financial_all` 解析财务数据。
- 同时从全文提取行业信息（`extract_industry_from_content`）。
- 返回包含财务指标和行业解析结果的字典，`fetch_success` 标记是否成功。
- 失败时记录到全局错误日志（加锁）。

### 7.2 批量并发获取：`fetch_stock_batch(stocks, workers)`

- 使用 `ThreadPoolExecutor(max_workers=workers)` 并发调用 `fetch_stock_finance`。
- 进度监控：每完成20只输出进度（耗时、失败/空计数）。
- 空结果检测：若 `annual_roe`、`annual_gross_margin`、`annual_debt_ratio` 均为 `None` 则记为空/失败，连续出现达到 `PAUSE_CONSECUTIVE_EMPTY` 则暂停 `PAUSE_DURATION` 秒。
- 全局超时控制：若总耗时超过 `GLOBAL_TIMEOUT`，立即 shutdown 线程池（兼容 Python <3.9）。
- 异常处理：`CancelledError`（任务取消）、其他 `Exception` 均记录日志，并将错误标记存入结果。
- 返回值：所有股票的原始数据列表。

### 7.3 财务报告解析器：`FinancialReportParser`

- `_split()`：按日期字符串（如 `2024年12月31日`）分割文本，形成多个段落。
- `_classify()`：识别年报（`annual`）、季报（`quarterly`）、半年报（`semi_annual`）；内容为 `None` 时返回 `unknown`。
- `latest(rtype)`：返回指定类型的最新段落（按日期降序）。
- `extract(seg)`：从段落文本中提取关键财务指标：
  - ROE（加权净资产收益率）
  - 毛利率、净利率
  - 营收同比增长率、净利润同比增长率
  - 资产负债率
  - 营业收入（带单位自动换算：万亿/亿/万/千/元）
  - 净利润、扣非净利润、经营活动现金流量净额
  - 经营现金流/净利润（比值）
  - 总资产周转率、应收账款周转率

  所有提取使用正则，带多种模式容错。

### 7.4 综合解析函数：`parse_financial_all(content)`

- 调用 `FinancialReportParser`，优先取年报段落（`annual`），其次最新季报/半年报。
- 若未提取到年报ROE，则对全文做一次粗略提取作为兜底。
- 返回统一命名的字典（`annual_roe`、`annual_gross_margin`、... `latest_revenue_yoy` 等）。

## 8. 行业识别与补调

### 8.1 内置表

- `_FALLBACK_INDUSTRY_MAP`：100条股票代码到一级行业的映射，优先使用。
- `SECONDARY_TO_PRIMARY`：二级行业到一级行业映射。
- `NAME_KEYWORD_INDUSTRY`：股票名称关键词到行业。
- `CODE_PREFIX_INDUSTRY`：代码前缀到行业。
- `standardize_industry()`：标准化行业名称（去掉"申万"等，统一2021版申万一级行业名称）。

### 8.2 从文本提取行业：`extract_industry_from_content(content)`

- 用多个正则匹配 `所属一级行业`、`申万行业`、`行业分类` 等字段。
- 若一级未找到，尝试提取二级行业并通过 `SECONDARY_TO_PRIMARY` 转换。
- 返回标准化后的一级行业名。

### 8.3 行业API补调：`fetch_industry_by_api(ts_code, name)`

- 发起两次查询：`所属申万行业`、`所属行业`，对返回文本再调用 `extract_industry_from_content`。
- 失败则记录错误日志。

### 8.4 批量补调：`batch_industry_patch(stocks)`

- 对未分类股票列表，用线程池（`INDUSTRY_API_WORKERS`）调用 `fetch_industry_by_api`。
- API补调失败的股票，再用名称关键词规则推断。
- 返回 `{ts_code: 行业}` 的映射字典。

### 8.5 主流程中的行业赋值顺序（优先级从高到低）

1. 财务文本中解析出的行业（`industry_l1_parsed`）
2. 外部完整行业映射表 `industry_map_full`（根据代码）
3. 数据库中已有的 `industry_l2` → 通过 `SECONDARY_TO_PRIMARY` 转换
4. 名称关键词推断（`infer_industry_from_name`）
5. 行业API补调（`batch_industry_patch`）
6. 代码前缀推断（`infer_industry_from_code_prefix`）

## 9. 数据库与缓存

数据库文件：`stock_cache.db`，包含两张表。

- `stocks`：股票基本信息（`ts_code`、`name`、`industry_l1`、`industry_l2`、更新时间）
- `financial_reports`：财务报告数据，以 `(ts_code, report_date, report_type)` 唯一。

### 9.1 缓存有效性判断：`should_refresh(conn, ts_code)`

- 若没有最新年报或季报记录，需刷新。
- 使用 `is_report_outdated` 检查报告是否过期：
  - **年报**：若当前时间在次年4月30日前，不算过期；否则判断距今 >400天为过期。
  - **季报/半年报**：距今 >100天为过期。
- 两者均未过期则不需要刷新，从缓存合并数据。

### 9.2 缓存合并：`merge_latest_reports(conn, ts_code)`

- 分别查询最新 `annual` 和 `quarterly/semi_annual` 报告，以及 `stocks` 表信息。
- 合并成与实时获取相同结构的字典，`fetch_success=True`。

### 9.3 数据存储

- `save_reports_batch`：批量插入/替换财务报告。
- `update_stocks_batch`：批量更新股票基本信息。

## 10. 评分系统

### 10.1 数据准备：`build_industry_stats(all_results)`

- 遍历所有非 `error` 结果，按行业分组，构建各行业和全市场的指标列表：
  - `roe_list`、`gross_margin_list`、`net_margin_list`
  - `revenue_yoy_list`、`profit_yoy_list`、`ocf_ratio_list`、`debt_ratio_list`
- 返回行业统计字典（`stats`）和全市场统计字典（`fallback`）。

### 10.2 百分位评分：`percentile_score(value, values, higher_better)`

- 过滤有效数值（`int/float`），样本数 < `MIN_INDUSTRY_SAMPLES`（5）时返回 `None`。
- 计算值在样本中的百分位：`(低于value的个数 + 0.5 × 等于value的个数) / 总数 × 100`。
- 若 `higher_better=False`（如负债率），则用 `100 - 百分位`。

### 10.3 完整度：`compute_completeness(r)`

- 统计7个核心指标非 `None` 的比例。
- ≥0.7 为"高"，≥0.4 为"中"，否则为"低"。

### 10.4 综合评分：`calc_score(stock, industry_stats, fallback)`

- **确定使用行业数据还是全市场数据**：
  - 若股票有明确行业且该行业样本量足够，使用行业统计；
  - 否则使用全市场数据并乘以折扣 0.95。
- **对每个指标**：
  - ROE若为负数，直接判定为0分（盈利质量差），不参与百分位排名。
  - 其他指标计算百分位评分，若行业样本不足则回退到全市场。
- **子维度得分计算**：
  - 盈利评分 = (roe分×0.4 + 毛利率分×0.3 + 净利率分×0.3) / 权重和（缺失指标不参与加权）
  - 成长评分 = (营收同比分×0.4 + 利润同比分×0.6) / 权重和
  - 现金流评分 = ocf_ratio分（缺失默认50）
  - 偿债评分 = debt_ratio分（缺失默认50）
- **总评分** = 四大维度加权求和，权重按实际存在的指标动态调整。
- **惩罚项**：
  - 若净利润 < 0 且 经营现金流 < 0，总分上限限制为15。
  - 完整度"低"时总分乘以 0.9。
- **评级**：

  | 分数 | 评级 |
  |------|------|
  | ≥75 | A |
  | ≥55 | B |
  | ≥40 | C |
  | ≥25 | D |
  | <25 | E |

- **置信度**：同完整度等级。
- 返回总评分、评级、子评分、评分基准、完整度、置信度。

## 11. 报告生成

### 11.1 Excel报告：`generate_report(results, output_dir, error_list, failed_stocks)`

使用 `pandas` 构建 DataFrame，包含：股票代码、名称、一级行业、各项财务指标、子评分、总评分、评级、置信度、评分基准、数据完整度。

- 按评级（A→E）和总评分降序排序。
- **多个工作表**：

  | 工作表 | 内容 |
  |--------|------|
  | 综合评价结果 | 全部股票 |
  | A级股票 ~ E级股票 | 按评级分sheet |
  | 低置信度股票 | 筛选置信度"低"的股票 |
  | 异常日志 | 全局错误记录 |
  | 获取失败股票 | 最终抓取失败的股票列表 |
  | 统计概览 | 数量统计、平均分、最高分、完整度分布等 |

- 文件命名：`股票业绩评价_<时间戳>.xlsx`

### 11.2 JSON输出

- 输出所有有评分的股票，按总评分降序。
- 文件名：`股票分析数据_<时间戳>.json`

## 12. 主流程（main函数）

1. 解析命令行参数，若 `--test` 则运行自测并退出。
2. 依据 `--base-dir` 等参数更新 Config 中的路径，确保目录存在。
3. 初始化日志。
4. 检查 `pandas/openpyxl` 依赖，缺失则退出。
5. 加载股票列表，为空则退出。
6. 初始化数据库，加载完整行业映射表。
7. **缓存判断**：
   - `--force-refresh` 则全部重新获取。
   - 否则遍历股票列表，`should_refresh` 决定是否需要获取，其余从缓存合并。
   - 输出缓存命中/需获取数量。
8. 若有需获取股票，调用 `fetch_stock_batch` 进行并发获取。
9. 若启用失败重试（`RETRY_FAILED_FINANCE`）：
   - 筛选 `fetch_success` 为 `False` 的结果，按 `MAX_RETRY_FAILED_ITEMS` 限制数量。
   - 逐个重试，每次输出进度和结果，间隔0.5秒。
10. 保存新获取的数据到数据库（年报、季报、股票基本信息）。
11. 合并缓存数据与新鲜数据 → `all_results`。
12. **行业赋值流程（未分类处理）**：
    - 遍历 `all_results`，对未分类股票依次尝试外部映射表、二级行业转换、名称推断。
    - 仍未分类的纳入 `unclassified` 列表。
    - 启用行业API补调时，对 `unclassified` 调用 `batch_industry_patch`。
    - 补调后仍为"未分类"的，尝试代码前缀推断。
13. 构建行业/全市场统计。
14. 对所有非 `error` 的股票计算评分。
15. 构建最终失败列表（仅含 `error` 或 `fetch_success==False` 的股票）。
16. 生成Excel报告和JSON文件。
17. 关闭数据库连接，输出完成信息。

## 13. 自测模式

- 运行 `python stock_analyzer.py --test`
- 使用内置测试文本验证财务解析器，断言关键指标（ROE 18.0%、毛利率45.6%等）。
- 通过则打印"自测通过"，否则断言失败退出。

## 14. 多线程安全与容错

- 全局错误日志 `error_log` 使用 `threading.Lock` 保护。
- 线程池关闭操作兼容 Python 3.6~3.12（自动判断 `cancel_futures` 参数）。
- 空结果暂停机制防止在数据源大面积失效时空耗资源。
- 重试上限避免极端情况下无限重试导致流程卡死。
- 所有子调用均捕获异常，记录到 `error_log` 或日志文件，不中断整体流程。

## 15. 命令行参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--base-dir` | 脚本所在目录 | 工作目录 |
| `--stock-file` | `xuan.txt` | 股票列表文件名 |
| `--workers` | 8 | 并发线程数 |
| `--force-refresh` | 否 | 忽略缓存全量更新 |
| `--no-retry-failed` | 否 | 禁用失败重试补采 |
| `--no-industry-patch` | 否 | 禁用行业API补调 |
| `--timeout` | 3600 | 全局超时秒数（0=不限） |
| `--test` | 否 | 运行内置自测并退出 |

## 16. 典型运行示例

```bash
# 指定工作目录和股票列表，6线程并发
python stock_analyzer.py --base-dir ./workplace --stock-file mylist.txt --workers 6

# 强制刷新缓存
python stock_analyzer.py --force-refresh

# 禁用失败重试和行业补调
python stock_analyzer.py --no-retry-failed --no-industry-patch
```
