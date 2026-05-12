# 2026-04-26 Daily Log

## 股票分析系统文档更新

### 完成工作
1. **确认 akshare 行业级别**：运行 `test_sw_level.py` 确认 `sw_index_first_info()` + `index_stock_cons("801xxx")` 返回的是**申万一级行业**（31个），非二级（131个）
2. **全面重写 README.md**：
   - 与代码逻辑完全对齐（6级行业判定、四维评分、置信度、完整度折扣等）
   - 新增行业判定策略表格、评分计算流程、指标提取规则
   - 补充 akshare 缓存机制、配置参数表、Excel输出列说明
   - 新增 FAQ 常见问题
3. **统一版本号**：代码文件头和 main() 输出从 5.2.0 → 6.0.0

### 关键结论
- akshare 取的是申万**一级**行业（31个，代码801xxx）
- 选择一级原因：100%覆盖、行业池足够大、稳定性好
- 二级行业131个会导致很多细分行业<5只，反而触发全市场折扣

### 文件变更
- `D:\Project\AnnualScorer\README.md` — 全面重写
- `D:\Project\AnnualScorer\annual_scorer.py` — 版本号 5.2.0 → 6.0.0（2处）

## README 文档逻辑修正（第二轮）

### 修正内容
1. **置信度阈值**：高置信度从 ≥6/8(≥85.7%) 修正为 ≥7/8(≥87.5%)，中置信度从 ≥4/8(≥57.1%) 修正为 ≥5/8(≥62.5%)，低置信度范围从 2~3 修正为 2~4
2. **配置参数表**：
   - `FINANCE_WORKERS`: 16 → 4
   - `API_RETRY_TIMES`: 2 → 3
   - 新增 `API_RETRY_BACKOFF_BASE` = 5.0
   - 新增 `PAUSE_CONSECUTIVE_EMPTY` = 5
   - 新增 `PAUSE_DURATION` = 30
3. **FAQ**：减少线程数建议从 `--workers 8` 改为 `--workers 2`

### 根因
代码调整后（降线程、加重试）未同步更新文档，导致文档与代码不一致
