# 2026-04-26 工作日志

## 项目：业绩评分_季报 V6.0.0

### 完成的工作

1. **全面逻辑审计**：编写并运行了40项单元测试，覆盖 parse_num、_extract_quarterly_block、percentile_rank、calc_completeness、评分集成等核心函数

2. **修复 percentile_rank 算法 bug**（严重）：
   - 原代码：升序中找第一个 `value >= v` 的位置，导致最大值返回0分
   - 修复：升序中找第一个 `v >= value` 的位置，降序中找第一个 `v <= value` 的位置
   - 影响：所有股票的评分结果都会变化

3. **统一版本号**：代码注释从 V5.0.0 → V6.0.0，与 argparse 和 README 一致

4. **更新 README**：
   - 版本号 V5.0.0 → V6.0.0
   - 代码行数 659 → 810行/679行代码
   - 补充数据完整性惩罚说明（ultra_low = 0.9 × 0.75 = 0.675）
   - 补充特殊规则（负ROE、负利润+负OCF上限、百分位算法说明）

5. **确认无需修复的问题**：
   - `--test` 模式已有 `setup_logging()` 调用（在 main 开头）
   - Excel 季报分数列正确（来自 calc_quarterly_score 返回值）
   - ULTRA_LOW_COMP_PENALTY=0.75 是额外系数，最终 0.9×0.75=0.675 与 README 一致

### 测试结果
- 单元测试：40/40 通过
- 自测：8/8 通过
- 语法检查：通过

---

## 项目：QAScorer (d:\Project\QAScorer) - 下午/晚上工作

### 修复 qa_scorer.py V6.2.1

1. **修复 SyntaxError：未闭合的 triple-quoted string**（严重）
   - 第3行 `"""` 开启了模块 docstring，但缺少闭合的 `"""`
   - 导致整个文件被解析为一个字符串，所有后续代码报 SyntaxError
   - 修复：在第5行后添加闭合 `"""`

2. **修复 raw string 转义警告**（Python 3.14 兼容性）
   - `r"\d"` 和 `r"\."` 在 Python 3.14 中被视为无效转义序列
   - 修复：将 `\d` 替换为 `[0-9]`，将 `\.` 替换为 `[.]`

3. **修复 NeoData API 响应解析**（严重）
   - 原代码取 `data["data"].get("text", "")`，但新版 API 返回结构为 `data["data"]["apiData"]["apiRecall"][i]["content"]`
   - 修复：重写 `run_neodata` 解析逻辑，支持新版 apiRecall 结构
   - 同时添加了对 `docData.docRecall` 的兼容支持
   - 处理了 `data["data"]` 为 None 的情况（某些股票 API 返回空数据）

### 运行结果
- 28只股票中19只成功获取数据（8只缓存+11只新获取），9只失败（API返回null）
- 最高分：鼎泰高科 73分（B级），金海通 70.5分（B级）
- 无A级股票（≥75分），可能因为样本量小且部分指标缺失

### 踩坑经验
- Python 3.14 对 raw string 中的反斜杠更严格，`\d`、`\.` 等会触发 SyntaxWarning 并可能导致解析失败
- Windows cp936 编码环境下，Python 源文件的 UTF-8 中文字符需要确保文件有正确的 coding 声明
- NeoData API 对某些股票返回 `"data": null`，需要做空值处理
- API 响应结构已从 `data.text` 改为 `data.apiData.apiRecall[i].content`

---

## qa_scorer.py 升级至 V6.3.0（晚上 21:00-21:30）

### 用户需求（5项）
1. 调整 Excel 行业逻辑，与 `@D:/Project/AnnualScorer/annual_scorer.py` 申万一级行业一致
2. 脚本输出只有 Excel 和 log，移除 JSON 输出
3. Excel 字段增加：净利润(元)(年报)、经营现金流(元)(年报)、偿债风险
4. Excel 中 ROE(年报)、净利润(元)(年报)、经营现金流(元)(年报)、负债率(年报) 取最新年报数据，其他字段取季报数据
5. 各维度评分与 `@D:/Project/AnnualScorer/annual_scorer.py` 评分逻辑一致

### 实现方案
- **版本**: V6.2.1 → V6.3.0
- **行业逻辑**: 与 AnnualScorer 完全一致（6级优先级：原文提取 → akshare申万 → 名称推断 → NeoData API → 本地映射表 → 代码前缀兜底）
- **数据来源分离**:
  - 年报字段（从 AnnualScorer/stock_cache.db 读取）: ROE、资产负债率、净利润(元)、经营现金流(元)
  - 季报字段（通过 NeoData API 获取）: 毛利率、净利率、营收同比、净利润同比
- **评分权重**: 与 AnnualScorer 对齐 → 盈利40% + 成长30% + 现金流20% + 偿债10%
- **percentile_rank 算法**: 与 AnnualScorer 一致 (count_leq/len * 100)
- **输出**: 只输出 Excel + log，无 JSON
- **Excel 字段**: 股票代码、名称、申万一级行业、ROE(%)、毛利率(%)、净利率(%)、营收同比(%)、净利润同比(%)、资产负债率(%)、OCF/净利润(%)、净利润(元)、经营现金流(元)、年报日期、数据完整度、总分、评级、置信度、盈利能力、成长性、现金流质量、偿债风险

### 文件信息
- 路径: `D:/Project/QAScorer/qa_scorer.py`
- 行数: 1362 行
- 大小: 47910 bytes
- 语法检查: 通过
- lint: 无错误

### 关键架构变更
- 新增 `load_annual_data_from_db()` 从年报数据库读取年报数据
- 新增 `merge_annual_quarterly()` 合并年报和季报数据
- 重写 `fetch_quarterly_batch()` 只获取季报字段
- `calc_score()` 权重与 AnnualScorer 对齐（40%+30%+20%+10%）
- `output_excel()` 字段与 AnnualScorer 一致，新增净利润(元)、经营现金流(元)、偿债风险列
- `main()` 移除 JSON 输出逻辑

### 踩坑经验
- 文件被上次中断的 write_to_file 清空为 0 字节，需要从头写入大文件时分段处理（write_to_file + replace_in_file）
- 写入超长文件时 Execution Cancelled，改用 replace_in_file 分段追加更可靠
