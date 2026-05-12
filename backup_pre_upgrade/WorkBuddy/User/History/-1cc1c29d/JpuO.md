# 2026-04-28 工作日志

## v3.1 性能优化与全量测试

### 优化内容
1. **全市场行情预加载缓存**：新增 `preload_market_data()` 函数，启动时一次拉取5000+行数据，后续查缓存O(1)
2. **NeoData缓存**：添加 `_neodata_cache` 避免同一股票重复调用NeoData子进程
3. **缓存TTL延长**：从5分钟延长到10分钟，适配4000+股票长时间运行
4. **main.py集成预加载**：fetch-only模式启动前自动调用 `preload_market_data()`

### Bug修复
1. **UnicodeDecodeError**：subprocess 调用 NeoData/westock-data 时 Windows GBK 编码崩溃 → 改用二进制模式 + UTF-8 解码
2. **NeoData正则匹配失败**：`总市值(亿元):10,146.32` 无空格 → 改为 `\s*[:：]\s*`
3. **ann_date字符串比较**：DB读取后 ann_date 为字符串，无法与 Timestamp 比较 → 添加 `pd.to_datetime()` 转换
4. **report_date字符串**：同上，calculator.py 的 `_split_quarterly()` 添加类型检查和转换

### 数据源优先级调整
- 原优先级：东方财富个股 → 全市场行情 → NeoData
- 新优先级：**全市场行情缓存** → 东方财富个股 → NeoData兜底
- 全市场行情缓存一次拉取5000+行，后续O(1)查询，大幅减少网络请求

### stock_pool.txt
- 实际包含 **4344只A股**（含沪深主板+创业板+科创板）
- 使用 `AkShare.stock_info_a_code_name()` 生成，已过滤ST/退市/北交所

### 全量运行参数
```bash
python main.py --real --pool stock_pool.txt --workers 8 --rate-limit 0.1 --save-db --fetch-only --db stock_data.db
python main.py --pool stock_pool.txt --from-db --db stock_data.db --output score_result.xlsx
```

### 版本号
- v3.0 → v3.1

---

## v3.1.1 Excel字段零值Bug修复

### 问题
用户反馈 Excel 中「净现比(OCFtoProfit)」和「ROE(%)(TTM)」值为0

### 根因分析
1. **`net_profit_ex`（扣非净利润）从未被获取** — `PROFIT_METRICS` 缺少 `index_deduct_holder_net_profit`，`FINAL_COLS` 缺少 `net_profit_ex`
2. **Calculator 误判** — `q_net_profit_ex` 全为0（不是NaN），但 `isna().all()` 返回False，导致用0值计算 `roe_ttm` 和 `net_profit_ratio`
3. **`fin_expense` 双列冲突** — `interest_expenses` 和 `financial_interest_expenses` 都映射到 `fin_expense`，dedup保留值较小的那个
4. **000858财务费用字段名不同** — API 返回 `benefit_finance_fee` 而非 `interest_expenses`

### 修复内容
1. **data_provider.py**:
   - 添加 `index_deduct_holder_net_profit` 到 `PROFIT_METRICS` 和 `PROFIT_COLS`
   - 添加 `net_profit_ex` 到 `FINAL_COLS`
   - 添加 `benefit_finance_fee` 到 `PROFIT_METRICS`（作为 `interest_expenses` 的备选）
   - 在 rename 前合并 `interest_expenses` 和 `benefit_finance_fee`（优先用前者）
   - 移除 `financial_interest_expenses` 映射避免重名列冲突
2. **calculator.py**:
   - 修复 `q_net_profit_ex` 判断：从 `not isna().all()` 改为 `(df['q_net_profit_ex'] != 0).any()`
   - 确保扣非净利润有实际非零值时才使用，否则回退到归母净利润

### 验证结果（600519+000858）
- `roe_ttm`: 35.07 / 19.93 ✅（之前为0）
- `net_profit_ratio`: 0.96 / 1.14 ✅（之前为0）
- `interest_cover`: 741.18 / 15.26 ✅（之前为0）
- `fin_expense` DB值: 40.9M / 2.03B ✅（之前为0）
- 所有Excel字段均为非零值 ✅

---

## v3.1.2 全字段取数逻辑审计 + 性能优化

### 审计范围
5只不同特征股票端到端验证：600519(白酒)、000858(白酒)、601398(银行)、002415(科技)、600036(银行)

### 发现的问题与修复

#### 1. 银行股毛利率100%异常（已修复）
- **问题**：银行oper_cost=0（无传统营业成本），毛利率=(revenue-0)/revenue=100%
- **修复**：calculator.py `_calc_profitability()` 加保护，oper_cost=0时毛利率设为0
- 金融行业（银行/保险）不适用传统毛利率概念，0值是正确行为

#### 2. Calculator性能瓶颈（已优化）
- **问题**：`_split_quarterly()` 和 `_calc_yoy()` 用 iterrows 逐行遍历，单次239ms
- **修复**：预建(year,qtr)→index映射，用numpy数组操作替代逐行df.at
- **效果**：239ms → 48ms（5x提速），全链路55ms/只

#### 3. `_init_empty()` 缺少字段（已修复）
- **问题**：`cash_recovery_rate` 未在 `_init_empty()` 中初始化，空数据时可能AttributeError
- **修复**：添加到attrs列表

### 审计通过项
- ✅ 单季拆分→TTM求和逻辑正确（vs 累计值直接求和会导致重复计数）
- ✅ 利息覆盖倍数公式正确：(oper_profit + fin_expense) / fin_expense
- ✅ 边界case：fin_expense=0→interest_cover=0, 负净利润→负净现比, 高D/E不crash
- ✅ 银行股0值字段（毛利率/收现比/流动比率）是行业特性，非bug
- ✅ 一票否决：D/E>3.0的银行股总分=0，逻辑正确

### 性能基准
- DB读取：1.6ms/次
- Calculator：48ms/次
- Scorer：0.05ms/次
- 全链路：55ms/只（4000只预估3.7分钟）

### 银行股数据特征
- `operating_costs` → 空字符串（银行无传统营业成本）
- `total_current_assets`/`current_total_debt` → 空字符串（银行不区分流动/非流动）
- `sale_received_cash` → 空字符串（银行无销售收现）
- 这些字段在API中存在但值为空，data_provider转换后为0

---

## v3.1.2 第二轮代码审计 + 文档同步（2026-04-28 07:00）

### 新发现并修复的Bug

#### 1. 财务费用0值被误删（data_provider.py）
- **问题**：`interest_expenses` 合并逻辑中，`apply(lambda x: NA if x==0)` 把有效的0值（利息收入>支出时财务费用为0）替换为NA
- **修复**：改为只将空字符串转为NA，0值保留为有效数据（`.replace('', pd.NA).replace('0', 0)`）

#### 2. 同比计算索引不完整（calculator.py）
- **问题**：`_calc_yoy` 只对 `q_net_profit_parent` 建日期索引；有营收无净利润的行找不到去年同期
- **修复**：净利润和营收分别建 `date_idx_profit` / `date_idx_revenue` 两个索引

#### 3. 净利润列兼容性（calculator.py）
- **问题**：`_calc_ttm_and_leverage` 的 `dropna(subset=['q_net_profit_parent'])` 会丢弃只有扣非净利润的股票
- **修复**：改为 `has_profit = notna(q_net_profit_parent) | notna(q_net_profit_ex)`

#### 4. 配置注释错误（config.py）
- **问题**：`min_ocf_ttm` 注释写"扣分"，实际代码是"总分清零（一票否决）"
- **修复**：注释修正为"总分清零（一票否决）"

### 文档同步
- README.md：版本号 v3.1 → v3.1.2
- README.md：补充 v3.1.1 和 v3.1.2 完整更新日志
- main.py / data_provider.py / calculator.py：文件头版本号统一为 v3.1.2

### 版本号统一
- 所有文件头部版本号统一：v3.1.2
