# A股智能选股系统 v3.1.2

基于季报+年报的基本面量化评分系统，支持4000+股票大规模并发扫描、回测防未来函数、一票否决机制。

---

## 快速开始

```bash
# 1. 模拟测试（无需网络）
python main.py --mock --stocks 600519 000858

# 2. 真实数据评分（并发获取+评分）
python main.py --real --stocks 600519 000858 --workers 3 --rate-limit 0.5

# 3. 先存数据到数据库，再评分（推荐，支持断点续传）
python main.py --real --pool stock_pool.txt --workers 8 --rate-limit 0.1 --save-db --fetch-only --db stock_data.db
python main.py --pool stock_pool.txt --from-db --db stock_data.db --output score_result.xlsx

# 4. 回测（指定历史日期，防未来函数）
python main.py --real --stocks 600519 --date 2024-06-30

# 5. 禁用否决机制
python main.py --mock --stocks 600519 000858 --disable-veto
```

---

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--stocks` | - | 股票代码列表（空格分隔） |
| `--pool` | stock_pool.txt | 股票池文件路径（建议使用绝对路径） |
| `--workers` | 5 | 并发线程数（4000+股建议8） |
| `--rate-limit` | 0.3 | 请求间隔(秒)（4000+股建议0.1） |
| `--date` | 今天 | 评估日期 (YYYY-MM-DD)，用于防未来函数 |
| `--output` | - | Excel 输出文件名 |
| `--mock` | False | 模拟模式（无需网络，随机生成数据） |
| `--real` | False | 真实数据模式（从 API 获取） |
| `--save-db` | False | 获取数据并保存到数据库 |
| `--from-db` | False | 从数据库读取财务数据评分 |
| `--fetch-only` | False | 仅获取数据存 DB，不评分 |
| `--db` | stock_data.db | 数据库文件路径 |
| `--disable-veto` | False | 禁用一票否决机制 |

### 大规模运行推荐参数

```bash
# 4000+股票全量获取（约30-60分钟，workers=8）
python main.py --real --pool stock_pool.txt --workers 8 --rate-limit 0.1 --save-db --fetch-only --db stock_data.db

# 评分输出（约1-2分钟）
python main.py --pool stock_pool.txt --from-db --db stock_data.db --output score_result.xlsx
```

---

## 系统架构

### 数据流

```
                    ┌─────────────────────────────────────────────────┐
                    │                    main.py                        │
                    │            CLI 入口 · 参数解析 · 结果输出          │
                    └──────────────┬──────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │       StockDatabase          │
                    │    SQLite 数据持久化层        │
                    └──────────────┬──────────────┘
                                   │
          ┌────────────────────────▼────────────────────────┐
          │                  DataProvider                    │
          │     多数据源获取 + 自动降级 + 字段标准化          │
          │   (启动时预加载全市场行情缓存，后续O(1)查询)      │
          │   (公告日估算: 年报120天 / 中报60天 / 季报30天)  │
          └────────────────────────┬────────────────────────┘
                                   │
          ┌────────────────────────▼────────────────────────┐
          │              IndicatorCalculator                 │
          │   公告日过滤 · 单季拆分 · TTM汇总 · 杠杆计算     │
          │   (同比计算: ≤去年同期取最近一条，防节假日偏移)   │
          └────────────────────────┬────────────────────────┘
                                   │
          ┌────────────────────────▼────────────────────────┐
          │                   Scorer                         │
          │     五维评分 · 一票否决 · 评级 · FCF Yield       │
          └─────────────────────────────────────────────────┘
```

### 数据源优先级

| 数据类型 | 主源 | 备用1 | 备用2 |
|----------|------|-------|-------|
| 财务数据（三表） | AkShare 同花顺 | - | - |
| 股票名称 | 全市场行情缓存 | 东方财富个股信息 | NeoData |
| 行业分类 | 东方财富个股信息 | westock-data profile | NeoData |
| 总市值 / PE-TTM | 全市场行情缓存 | 东方财富个股信息 | NeoData |

> **说明**：
> - 启动时自动预加载全市场行情缓存（`stock_zh_a_spot_em`），后续股票名称/市值/PE直接查缓存，O(1)速度
> - 东方财富 `stock_individual_info_em` 接口在当前网络环境下可能被拒绝（RemoteDisconnected），系统会自动降级
> - NeoData 作为最终兜底，保证数据完整性
> - 全市场行情缓存有10分钟TTL，超时自动刷新

### 模块说明

| 模块 | 职责 |
|------|------|
| `main.py` | CLI 入口、参数解析、并发评估、Excel 导出 |
| `data_provider.py` | 多数据源获取（AkShare/东方财富/westock-data/NeoData）、三表合一、公告日估算、字段标准化、自动降级、全市场行情预加载缓存 |
| `calculator.py` | 公告日过滤、单季拆分、TTM汇总、杠杆/同比计算 |
| `scorer.py` | 五维评分、一票否决、FCF Yield 计算、评级生成 |
| `database.py` | SQLite 数据层、财务数据/行情/评分持久化、断点续传 |
| `config.py` | 全局配置（权重、阈值、否决规则） |
| `utils.py` | 辅助工具（ST过滤、日历、股票池加载） |
| `batch_runner.py` | 独立并发运行器（含断点续跑，可选使用） |
| `utils_cache.py` | SQLite JSON 缓存（可选，与 database.py 二选一） |

---

## 五维评分模型

### 总分公式

```
总分 = 成长性×25% + 盈利能力×30% + 现金流质量×20% + 偿债风险×15% + 估值×10%
```

### 1. 成长性（权重 25%）

| 指标 | 字段 | 权重 | 满分阈值 |
|------|------|------|----------|
| 单季营收同比 | `q_revenue_yoy` | 40% | ≥30% |
| 单季净利润同比 | `q_net_profit_yoy` | 60% | ≥50% |

```
成长性 = 营收同比得分×0.4 + 净利润同比得分×0.6
得分 = min(100, value / threshold × 100)
```

### 2. 盈利能力（权重 30%）

| 指标 | 字段 | 权重 | 满分阈值 |
|------|------|------|----------|
| TTM ROE | `roe_ttm` | 70% | ≥15% |
| TTM 毛利率 | `gross_margin_ttm` | 30% | ≥40% |

```
盈利能力 = ROE得分×0.7 + 毛利率得分×0.3
```

### 3. 现金流质量（权重 20%）

| 指标 | 字段 | 权重 | 满分阈值 |
|------|------|------|----------|
| 净现比 | `net_profit_ratio` | 40% | ≥1.0 |
| FCF收益率 | `fcf_yield` | 30% | ≥3% |
| 收现比 | `cash_recovery_rate` | 30% | ≥1.0 |

```
净现比 = OCF / 净利润
FCF收益率 = (OCF - Capex) / 总市值
收现比 = 销售收现 / 营收

现金流质量 = 净现比得分×0.4 + FCF收益率得分×0.3 + 收现比得分×0.3
```

### 4. 偿债风险（权重 15%）

| 指标 | 字段 | 权重 | 满分阈值 |
|------|------|------|----------|
| D/E | `de_ratio` | 40% | ≤0.5（反向） |
| 流动比率 | `current_ratio` | 30% | ≥2.0 |
| 资产负债率 | `asset_liability_ratio` | 30% | ≤50%（反向） |

```
偿债风险 = D/E得分×0.4 + 流动比率得分×0.3 + 资产负债率得分×0.3
反向指标得分 = min(100, (1 - value / threshold) × 100)
```

### 5. 估值（权重 10%）

| 指标 | 字段 | 满分阈值 |
|------|------|----------|
| PE-TTM | `pe_ttm` | ≤20（反向） |

```
估值 = min(100, (1 - PE / 20) × 100)
PE ≤ 0 时得 0 分
```

---

## 一票否决机制

总分触及以下任一条件时，**总分直接清零**：

| 规则 | 条件 |
|------|------|
| 现金流得分 | < 20 分 |
| D/E | > 3.0 |
| 资产负债率 | > 90% |
| 经营现金流 | < 0 亿元 |

---

## 防未来函数

使用 `ann_date`（公告日）过滤，只用评估日前已公告的财报。

若某财报在评估日之后才公告，该财报不参与计算。回测时务必使用 `--date` 指定历史日期。

公告日估算规则：年报 +120天 / 中报 +60天 / 季报 +30天

---

## 断点续传

`--fetch-only` 模式下，系统会自动跳过已有足够数据（≥4季度）的股票，仅获取缺失数据。中断后重新运行即可继续。

```bash
# 第一次运行（可能中断）
python main.py --real --pool stock_pool.txt --workers 8 --rate-limit 0.1 --save-db --fetch-only --db stock_data.db

# 重新运行（自动跳过已有数据）
python main.py --real --pool stock_pool.txt --workers 8 --rate-limit 0.1 --save-db --fetch-only --db stock_data.db
```

---

## Excel 输出

| 维度 | 字段 | 说明 |
|------|------|------|
| 基础信息 | symbol, name, industry, dates | 股票信息 |
| 成长性 | q_revenue_yoy, q_net_profit_yoy, growth | 单季同比 + 得分 |
| 盈利能力 | roe_ttm, gross_margin_ttm, profitability | TTM指标 + 得分 |
| 现金流质量 | net_profit_ratio, fcf_yield, cash_recovery_rate, cash_flow_quality | 三个比率 + 得分 |
| 偿债风险 | de_ratio, current_ratio, asset_liability_ratio, leverage_risk | 杠杆指标 + 得分 |
| 估值 | pe_ttm, total_mv | PE + 市值 |
| 综合 | total_score, rating, confidence | 总分 + 评级 |
| 否决 | veto, veto_reason | 否决状态 |

### Excel 颜色方案

| 维度 | 背景色 |
|------|--------|
| 基础信息 | ⬜ 白色 |
| 成长性 | 🔵 蓝色 |
| 盈利能力 | 🟢 绿色 |
| 现金流质量 | 🟠 橙色 |
| 偿债风险 | 🟡 深橙 |
| 估值 | 🟣 紫色 |
| 综合 | 🟨 金色 |
| 否决 | ⬛ 灰色 |

### 评级颜色

| 评级 | 颜色 |
|------|------|
| A+/A | 深绿 |
| B+/B | 浅绿 |
| C | 黄色 |
| D | 红色 |

---

## 项目结构

```
ScoreSys/
├── config.py           # 全局配置（权重/阈值/否决规则）
├── data_provider.py    # 多数据源获取（AkShare/东方财富/westock-data/NeoData）+ 预加载缓存
├── calculator.py       # 指标计算（单季拆分+TTM+杠杆+同比）
├── scorer.py           # 五维评分 + 一票否决 + FCF Yield + 评级
├── database.py         # SQLite 数据层（财务数据/行情/评分持久化）
├── main.py             # CLI 入口 + 并发评估 + Excel 导出
├── batch_runner.py     # 独立并发运行器（含断点续跑，可选）
├── utils_cache.py      # SQLite JSON 缓存（可选，与 database.py 二选一）
├── utils.py            # 辅助工具（ST过滤/日历/股票池加载）
├── stock_pool.txt      # 股票池文件（4344只A股）
├── stock_data.db       # SQLite 数据库（运行时生成）
└── requirements.txt    # 依赖清单
```

---

## 依赖

```
akshare>=1.12.0
pandas>=1.5.0
numpy>=1.21.0
openpyxl>=3.0.0
```

Python 版本：3.8+

---

## 更新日志

### v3.1.2（2026-04-28）

**Bug 修复：**
- **净现比/ROE为0修复**：`PROFIT_METRICS` 缺少 `index_deduct_holder_net_profit`（扣非净利润），导致 `net_profit_ex` 全为0；Calculator 判断有效性条件从 `not isna().all()` 改为 `(df[col] != 0).any()`，正确识别全0列
- **银行股毛利率100%修复**：银行 `oper_cost=0`，原公式 `(revenue-0)/revenue=100%`；修复为 `oper_cost=0` 时毛利率设为0（金融行业毛利率不适用）
- **财务费用0值误删修复**：`interest_expenses` 合并逻辑中，0值（利息收入>支出时）被错误替换为NA；修复后0值保留为有效数据
- **同比计算索引修复**：`_calc_yoy` 中净利润和营收分别建日期索引，避免有营收无净利润时找不到去年同期数据
- **净利润列兼容性修复**：`_calc_ttm_and_leverage` 中 `dropna` 只检查 `q_net_profit_parent`，改为同时兼容 `q_net_profit_ex`，防止只有扣非净利润的股票数据被丢弃
- **配置注释修正**：`min_ocf_ttm` 注释从"扣分"修正为"总分清零（一票否决）"，与实际代码行为一致

**性能优化：**
- Calculator 单次计算从 239ms 降至 48ms（5x提速）：`_split_quarterly` 和 `_calc_yoy` 从 `iterrows` 改为预建索引 + numpy 数组操作
- 全链路评分 55ms/只，4000只 from-db 评分预估 3.7 分钟

**数据源增强：**
- 添加 `benefit_finance_fee` 作为 `interest_expenses` 的备选字段（部分公司如000858五粮液只有此字段有值）
- 添加 `index_deduct_holder_net_profit` 到 `PROFIT_METRICS` 和 `FINAL_COLS`
- 财务费用合并逻辑：`interest_expenses` 优先，`benefit_finance_fee` 兜底（优先级合并，非覆盖）

**银行股数据特性确认（非bug）：**
- `operating_costs`/`total_current_assets`/`current_total_debt`/`sale_received_cash`：银行股API返回空字符串，转换后为0，属行业特性
- 银行 D/E > 3.0 触发一票否决是预期行为（银行天然高杠杆）

### v3.1.1（2026-04-28）

**Bug 修复：**
- 修复 `interest_expenses` 与 `financial_interest_expenses` 重名列映射冲突（dedup丢失数据）
- 修复 `_init_empty` 缺少 `cash_recovery_rate` 字段

### v3.1（2026-04-28）

**性能优化：**
- 新增全市场行情预加载缓存机制（`preload_market_data()`），启动时一次拉取5000+行数据，后续股票名称/市值/PE直接查缓存
- 缓存TTL从5分钟延长到10分钟，适配4000+股票长时间运行场景
- NeoData查询结果添加缓存（`_neodata_cache`），避免同一股票重复调用
- 全市场行情缓存查询失败时不再阻塞，直接走降级链

**Bug 修复：**
- 修复 Windows 下 `subprocess` 调用 NeoData/westock-data 时的 `UnicodeDecodeError`（改用二进制模式+UTF-8解码）
- 修复 NeoData 正则匹配失败（`总市值(亿元):` 后可能无空格，改为 `\s*[:：]\s*`）
- 修复从DB读取数据时 `report_date`/`ann_date` 为字符串导致 `.dt` 访问器和 `Timestamp` 比较报错
- 修复 PowerShell 下 `cd /d` 命令解析错误（改用绝对路径直接运行）

**数据源增强：**
- `_fetch_stock_info()` 优先级调整为：全市场行情缓存 → 东方财富个股信息 → NeoData兜底
- NeoData 查询改为 `--data-type api` 参数，返回结构化数据更易解析
- NeoData 一次返回名称+行业+市值+PE，减少重复调用

**文档更新：**
- 新增大规模运行推荐参数章节
- 数据源优先级表更新
- 架构图新增预加载缓存说明

### v3.0.1（2026-04-27）

**数据源增强：**
- 添加 westock-data 作为股票名称和行业的备用数据源
- 添加 NeoData 金融数据搜索作为总市值/PE-TTM 的备用数据源
- 东方财富接口被拒绝时自动降级，不再导致整个流程失败

**Bug 修复：**
- 修复 westock-data profile 解析 bug（lines[1] 是分隔符行，应取 lines[2] 作为数据行）
- 修复 subprocess 在 Windows PowerShell 下调用 npx 需要 `shell=True` 的问题

**验证：**
- 通过 600519（贵州茅台）和 000858（五粮液）验证全流程数据准确性
- 备用数据源全部验证通过：名称 ✅ 行业 ✅ 总市值 ✅ PE-TTM ✅
