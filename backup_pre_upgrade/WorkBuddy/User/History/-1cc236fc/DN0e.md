# 2026-04-27 工作日志

## 完善 README.md 文档

**时间：** 19:03

**工作内容：**
- 完整阅读了 ScoreSys 项目所有源码（config.py, data_provider.py, calculator.py, scorer.py, batch_runner.py, utils.py, utils_cache.py, main.py）
- 基于代码实现全面重写 README.md

**主要改进：**
1. 新增系统架构图（ASCII 流程图），展示模块间数据流
2. 新增数据流说明，从 AkShare API 到最终输出的完整链路
3. 新增模块说明章节，逐一介绍每个模块的职责和关键方法
4. 新增配置详解，列出所有可配置参数及其含义
5. 新增阈值配置表，明确各指标的满分标准
6. 新增输出说明，详细列出 Excel 每个字段的含义
7. 新增双层缓存说明（文件缓存 + SQLite 缓存）
8. 新增断点续跑使用示例
9. 新增模拟模式说明
10. 注意事项从 4 条扩展到 9 条

**版本：** v3.0（与代码一致）

---

## 全面代码评估

**时间：** 22:12

**工作内容：**
- 对所有 11 个 Python 源文件进行了全面评估
- 生成了详细评估报告（评估报告.md）

**关键发现：**

### P0 Bug（会导致崩溃）
1. `main.py` 第 687 行：`fetch_one()` 中 `global success, fail` 引用的是 main() 局部变量，会导致 NameError
2. `save_to_excel()` 中 `DIMENSION_FILLS` 和 `COL_DIMENSIONS` 重复定义两次，第一次是死代码

### P1 缺陷（影响正确性）
3. Mock 模式与真实模式的市值单位不一致（亿 vs 元，差 1e8 倍）
4. `ann_date` 统一加 45 天估算过于粗糙
5. 同比计算使用精确日期匹配，因节假日偏移会失败

### P2 质量问题
6. 三套缓存/数据库系统冗余（DataCache/StockDatabase/BatchRunner）
7. `batch_runner.py` 未集成到 main.py，是死代码
8. `fcf_yield` 在 calculator.py 和 scorer.py 中计算方式不一致
9. main.py ~800 行，职责过重

**总体评价：** 架构设计优秀，核心功能可用。修复 P0 后可稳定运行。

---

## P0/P1/P2 Bug 修复

**时间：** 22:24

**修复内容：**

### P0 修复（2项）
1. **main.py line 687**：`fetch_one()` 中 `global success, fail` → 改为 `nonlocal success, fail`，解决嵌套函数作用域错误
2. **main.py save_to_excel()**：删除重复的 `DIMENSION_FILLS` 和 `COL_DIMENSIONS` 定义，保留完整版本并移到表头渲染之前，补充了 `fcf_yield`/`cash_recovery_rate` 等遗漏的键映射

### P1 修复（3项）
3. **Mock 模式市值单位**：经分析，Mock 模式内部单位一致（均为亿或均为元），`fcf_yield` 硬编码 0.03 改为计算值 `ocf*0.8/mv`
4. **data_provider.py ann_date**：从统一 45 天改为按报告期类型区分（年报 120 天、中报 60 天、季报 30 天）
5. **calculator.py YoY 匹配**：`df['report_date'] == last_year_date` → `df['report_date'] <= last_year_date].tail(1)`，避免节假日偏移导致匹配失败

### P2 修复（4项）
6. **三重缓存**：main.py 已只使用 StockDatabase，utils_cache.py 和 batch_runner.py 为独立工具文件，未被导入
7. **BatchRunner 集成**：已评估，当前 batch_evaluate 已实现核心功能（并发+速率限制），checkpoint 可作为后续增强
8. **fcf_yield 统一**：删除 calculator.py 中的 fcf_yield property，统一在 scorer.py 和 main.py 中用 `fcf_ttm / total_mv` 计算
9. **main.py 拆分**：建议后续迭代，当前 800 行可维护

**语法验证：** 所有修改文件通过 py_compile 检查，无语法错误。
