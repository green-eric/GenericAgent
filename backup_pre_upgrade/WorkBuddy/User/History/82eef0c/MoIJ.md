# 2026-04-25 日志

## README.md 与 stock_analyzer.py 一致性修正

发现并修正了文档与代码之间的多处不一致：

### 修正项
1. **行业补调分批参数**：文档写的"每批 50 只，批间休眠 3s"，实际代码是 `BATCH_SIZE=100`，休眠 `1s`。已修正。
2. **行业补调线程数**：文档未提及，代码 `INDUSTRY_API_WORKERS=15`。已补充到文档。
3. **HTTPAdapter 重试次数**：财务数据获取 `max_retries=2`，行业补调 `max_retries=1`。文档已区分。
4. **API_RETRY_TIMES 语义**：文档写的"API 重试次数"，实际代码 `range(1, API_RETRY_TIMES+2)` 总尝试 3 次（1 初始 + 2 重试）。已修正为"额外重试次数"。
5. **配置项补充**：补充了 `INDUSTRY_API_WORKERS` 和 `INDUSTRY_CACHE_DAYS` 到配置速查表。
6. **代码清理**：移除未使用的 `import subprocess`（V5 已改为 requests 直连）。

### 关键代码参数备忘
- `BATCH_SIZE = 100`（行业补调每批数量）
- 行业补调批间休眠 `1s`
- `INDUSTRY_API_WORKERS = 15`
- 行业补调 adapter `max_retries=1`，财务 adapter `max_retries=2`
- `API_RETRY_TIMES=2` → 总尝试 3 次

## V5 净利润解析bug修复 (22:58)

### Bug根因
`parse_financial_all()` 中净利润行匹配逻辑 `l.startswith('净利润')` 会错误匹配到 `净利润现金含量160.44%` 行（因为该行也以"净利润"开头）。由于 `净利润现金含量` 行出现在年报段落的"现金流状况"章节（早于"盈利能力"章节中的真实 `净利润` 行），导致总是匹配到错误的行。`_parse_num_from_line` 无法从百分比行提取带单位的数值，返回 None。

### 影响范围
- **2863只股票**（共4344只）的 `annual_net_profit` 为 null
- 连锁导致 `annual_ocf_to_profit`（经营现金流/净利润）也为 null
- 这些股票的现金流评分被默认为50分（缺失填充值），影响了评分准确性

### 修复方案
在行匹配条件中增加排除项：
```python
if l.startswith('净利润') and '归母' not in l and '扣非' not in l \
        and '现金含量' not in l and '增长率' not in l and '同比' not in l:
```

### 其他修复
1. **JSON输出添加 `data_timestamp`**：在JSON根节点加入数据生成时间戳
2. **JSON输出添加 `annual_report_date`**：每只股票包含年报日期
3. **Excel报告添加年报日期列**：格式化为 YYYY-MM-DD
4. **`merge_latest_reports` 补充 `annual_report_date`**：缓存命中的股票也能正确输出年报日期
5. **自测数据更新**：使用更接近真实NeoData格式的数据（含净利润现金含量行）

### 验证结果
- 自测通过（含净利润现金含量干扰项的正确识别）
- 5只股票实查验证：净利润全部正确解析，OCF/净利润计算正确
- 原有解析正确的字段（ROE、毛利率等）不受影响
