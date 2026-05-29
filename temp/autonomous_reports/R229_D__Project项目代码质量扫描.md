# D:/Project 代码质量扫描报告

**扫描时间**: 2026-05-22 09:56
**工具**: ruff 0.15.13
**扫描范围**: D:/Project (AnnualScorer, BfM, ScoreSys)
**Python文件总数**: 242

---

## 📊 总览

| 项目 | 总问题 | 🔴 ERROR | 🟡 WARNING | 🔵 STYLE | ⚫ SECURITY |
|------|--------|----------|------------|----------|------------|
| AnnualScorer | 110 | 23 | 0 | 13 | 74 |
| BfM | 4109 | 1475 | 23 | 384 | 2227 |
| ScoreSys | 771 | 295 | 202 | 160 | 114 |
| **总计** | **4990** | | | | |

## 📁 AnnualScorer (110 issues)

### Top 10 规则

| 规则 | 描述 | 数量 |
|------|------|------|
| S101 | assert语句(生产代码) | 41 |
| S311 | 不安全的随机数 | 27 |
| F401 | import未使用 | 11 |
| C901 | 函数复杂度过高 | 7 |
| E501 | 行过长(>88字符) | 7 |
| I001 | import排序不规范 | 4 |
| S608 | SQL字符串拼接 | 3 |
| B905 | zip无strict参数 | 2 |
| E402 | import不在文件顶部 | 2 |
| F841 | 变量赋值未使用 | 2 |

### Top 10 问题文件

| 文件 | 问题数 |
|------|--------|
| D:/Project\AnnualScorer\annual_scorer.py | 44 |
| D:/Project\AnnualScorer\tests\test_scorer.py | 26 |
| D:/Project\AnnualScorer\tests\test_coverage_gap.py | 8 |
| D:/Project\AnnualScorer\api_client.py | 4 |
| D:/Project\AnnualScorer\fetcher.py | 4 |
| D:/Project\AnnualScorer\metrics.py | 4 |
| D:/Project\AnnualScorer\db.py | 3 |
| D:/Project\AnnualScorer\file_monitor.py | 3 |
| D:/Project\AnnualScorer\parser.py | 3 |
| D:/Project\AnnualScorer\config.py | 2 |

## 📁 BfM (4109 issues)

### Top 10 规则

| 规则 | 描述 | 数量 |
|------|------|------|
| S101 | assert语句(生产代码) | 2177 |
| E501 | 行过长(>88字符) | 1442 |
| I001 | import排序不规范 | 158 |
| C901 | 函数复杂度过高 | 135 |
| B007 | 循环变量未使用 | 37 |
| W293 | 空白行含空格 | 22 |
| S110 | try-except-pass | 18 |
| F401 | import未使用 | 16 |
| N806 | 变量命名不规范 | 13 |
| B023 | 闭包变量引用问题 | 13 |

### Top 10 问题文件

| 文件 | 问题数 |
|------|--------|
| D:/Project\BfM\tests\test_scorer_dimensions.py | 251 |
| D:/Project\BfM\tests\test_validators.py | 179 |
| D:/Project\BfM\tests\test_scorer.py | 162 |
| D:/Project\BfM\tests\test_data_quality_monitor.py | 140 |
| D:/Project\BfM\tests\test_error_handler.py | 140 |
| D:/Project\BfM\tests\test_performance_fix.py | 131 |
| D:/Project\BfM\tests\test_data_quality_api.py | 115 |
| D:/Project\BfM\modules\data_quality_monitor.py | 89 |
| D:/Project\BfM\tests\test_sector_extraction.py | 81 |
| D:/Project\BfM\modules\server\pipeline_manager.py | 79 |

## 📁 ScoreSys (771 issues)

### Top 10 规则

| 规则 | 描述 | 数量 |
|------|------|------|
| W293 | 空白行含空格 | 174 |
| E501 | 行过长(>88字符) | 84 |
| F541 | f-string无占位符 | 69 |
| I001 | import排序不规范 | 65 |
| E701 | 多语句单行 | 54 |
| S608 | SQL字符串拼接 | 51 |
| F401 | import未使用 | 48 |
| C901 | 函数复杂度过高 | 47 |
| S110 | try-except-pass | 25 |
| B007 | 循环变量未使用 | 16 |

### Top 10 问题文件

| 文件 | 问题数 |
|------|--------|
| D:/Project\ScoreSys\db_health_check.py | 93 |
| D:/Project\ScoreSys\archive\fusion_picker_v2.py | 58 |
| D:/Project\ScoreSys\evaluator.py | 54 |
| D:/Project\ScoreSys\backtest.py | 46 |
| D:/Project\ScoreSys\fetcher.py | 32 |
| D:/Project\ScoreSys\fill_industry_momentum.py | 32 |
| D:/Project\ScoreSys\fix_stocks_missing.py | 31 |
| D:/Project\ScoreSys\archive\factor_redundancy.py | 30 |
| D:/Project\ScoreSys\archive\industry_neutral_backtest.py | 29 |
| D:/Project\ScoreSys\diff_excel.py | 29 |

## 🔍 关键发现

### 1. 最严重问题 (SECURITY)

- **AnnualScorer**: 74个安全问题
  - S101 (assert语句(生产代码)): 41
  - S311 (不安全的随机数): 27
  - S608 (SQL字符串拼接): 3
- **BfM**: 2227个安全问题
  - S101 (assert语句(生产代码)): 2177
  - S110 (try-except-pass): 18
  - S310 (): 10
- **ScoreSys**: 114个安全问题
  - S608 (SQL字符串拼接): 51
  - S110 (try-except-pass): 25
  - S310 (): 12

### 2. 最严重问题 (ERROR)

- **AnnualScorer**: 23个错误
  - F401 (import未使用): 11
  - E501 (行过长(>88字符)): 7
  - E402 (import不在文件顶部): 2
- **BfM**: 1475个错误
  - E501 (行过长(>88字符)): 1442
  - F401 (import未使用): 16
  - E402 (import不在文件顶部): 7
- **ScoreSys**: 295个错误
  - E501 (行过长(>88字符)): 84
  - F541 (f-string无占位符): 69
  - E701 (多语句单行): 54

## 📈 技术债量化

| 指标 | 数值 |
|------|------|
| 总问题数 | 4990 |
| 平均每文件问题数 | 20.6 |
| 安全问题(需立即处理) | 2415 |
| 错误(需修复) | 1793 |
| 风格问题(可批量修复) | 557 |

## 💡 修复建议 (按优先级)

### P0 - 立即处理
1. **BfM S101 (assert语句)**: 2177个 — 生产代码中大量assert，建议用if/raise替换
2. **BfM E501 (行过长)**: 1442个 — 建议配置ruff line-length或批量格式化
3. **ScoreSys S608 (SQL拼接)**: 51个 — SQL注入风险，需参数化查询

### P1 - 近期处理
1. **ScoreSys W293 (空白行空格)**: 174个 — 可 `ruff check --fix` 自动修复
2. **ScoreSys F541 (空f-string)**: 69个 — 可批量修复
3. **BfM C901 (复杂函数)**: 135个 — 需重构拆分

### P2 - 可自动化修复
1. **I001 (import排序)**: 全部项目 — `ruff check --select I001 --fix`
2. **F401 (未使用import)**: 全部项目 — `ruff check --select F401 --fix`
3. **W293 (空白行空格)**: `ruff check --select W293 --fix`


---
*由 ruff 0.15.13 自动生成 | 2026-05-22 09:56*
