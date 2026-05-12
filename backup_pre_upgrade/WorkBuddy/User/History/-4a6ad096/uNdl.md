# 2026-04-26 工作日志

## README.md 重构优化
- 修复章节编号断裂（10→14→11→12→13 → 1→2→...→13 连续）
- 新增"快速开始"章节（环境要求、基本用法、输出文件）
- 合并输出字段说明到第10章"输出文件与字段说明"
- V5 变更用对比表集中展示
- 篇幅从 360 行精简至 ~260 行

## stock_analyzer.py 全面检查与修复
### 修复内容
1. **补充 Excel Sheet**：新增"低置信度股票"和"获取失败股票" Sheet，与文档对齐
2. **补充行业归属第③步**：`determine_industry()` 中增加 `SECONDARY_TO_PRIMARY` 二级→一级映射
3. **评分排除自身**：`calc_score()` 中 `pool_values()` 排除正在评分的股票自身，避免自影响排名
4. **文档同步更新**：
   - Excel Sheet 列表修正（8 个 Sheet）
   - 行业归属说明注明 `_FALLBACK_INDUSTRY_MAP` 和 `SECONDARY_TO_PRIMARY` 当前为空
   - 评分方法补充"排除自身"说明

### 自测结果
- 14 通过, 0 失败 ✅

### 未修改（经分析无需修改）
- `should_refresh()` 缓存逻辑：边界情况验证正确
- `parse_num()` / `_parse_num_from_line()` 数值提取：自测覆盖
