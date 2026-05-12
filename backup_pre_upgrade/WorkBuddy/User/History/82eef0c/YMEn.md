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
