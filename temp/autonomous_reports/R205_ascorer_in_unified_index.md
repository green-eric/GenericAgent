# AnnualScorer 纳入 GA 统一搜索索引报告

> 任务: 将 AnnualScorer 的报告/源码纳入 GA 的 autonomous_reports 统一索引
> 完成时间: 2026-05-19

## 背景
autonomous_reports 搜索索引已有 189 篇 GA 报告，AnnualScorer 项目源码未纳入。

## 实施

### 索引扩展
- 旧索引: 189 文件, 25545 terms
- 新索引: 204 文件, 10464 terms, 2.5MB
- AnnualScorer 新增 15 个文件：
  - .py: annual_scorer, api_client, config, db, exporter, fetcher, file_monitor, industry, metrics, parser, scorer, utils
  - .json: industry_map, industry_map_akshare
  - .md: README

### 搜索工具升级 (search_reports.py)
- 新增 `--source GA|AScorer` 过滤
- 结果显示来源标签 [GA] / [AnnualScorer]
- 支持 AnnualScorer 文件路径 (AScorer:relative/path)

### 验证
- "annual scorer" → 命中 AnnualScorer db.py + GA 相关报告
- "fetcher" → 5 results (GA 3 + AScorer 2)
- "exporter" → 4 results (GA 2 + AScorer 2)
- "--source AScorer scorer" → 仅返回 AnnualScorer 源码 (annual_scorer.py, scorer.py)

## 使用
```bash
python search_reports.py "annual scorer"
python search_reports.py "fetcher" --source AScorer
python search_reports.py "reversal 因子" --source GA
```
