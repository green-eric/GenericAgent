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
