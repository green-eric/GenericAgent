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
