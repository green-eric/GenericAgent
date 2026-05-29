# R239 - file_monitor_v3回测结果SQLite适配

## 背景
TODO要求将回测结果从PG写入改为SQLite本地存储，解除PG依赖。

## 发现
backtest_result_parser.py **已经完成了SQLite适配**：
- `init_db()` 使用 sqlite3 创建 `backtest_results` 表
- `insert_result()` 写入SQLite
- `process_all()` 主流程完全使用SQLite
- 无 psycopg2 实际调用

## 执行内容
1. **清理残留注释**：`# 依赖: psycopg2` → `sqlite3(standard library)`
2. **清理残留注释**：`# ── PostgreSQL入库 ──` → `# ── SQLite入库 ──`
3. **验证运行**：`parser --all` 正常处理4个回测文件
4. **验证查询**：SQLite数据库4条记录，3条success，1条failed

## 验收结果
- ✅ 回测JSON → SQLite写入OK
- ✅ SQLite查询OK
- ✅ 摘要Markdown生成OK
- ✅ 无PG依赖残留

## 数据样本
| # | 模式 | IC均值 | 夏普 | 最大回撤 | 总收益 | 胜率 | 状态 |
|---|------|--------|------|---------|--------|------|------|
| 5 | auto_file_monitor | - | 0.0 | 0.0 | 1.61 | 0.0 | success |
| 6 | ic | - | - | - | - | - | failed |
| 7 | ic | 0.188 | - | - | - | - | success |
| 8 | ic | 0.188 | 1.82 | -0.123 | 0.245 | 0.67 | success |
