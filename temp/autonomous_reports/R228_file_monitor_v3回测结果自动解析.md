# R228 | 能力 | file_monitor_v3回测结果自动解析

## 结论
✅ **backtest_result_parser.py 创建完成** — 自动解析回测JSON → 提取指标 → PG入库 → Markdown摘要生成。

## 功能验证结果

| 测试项 | 状态 |
|--------|------|
| 模块导入 | ✅ 正常 |
| 文件发现 (auto_bt_*.json) | ✅ 找到1个结果文件 |
| 扁平格式解析 (auto_bt样本) | ✅ total_return=1.61, sharpe=0, status=success |
| ic_result格式解析 | ✅ ic_mean=-0.0026, ic_std=0.105, positive_pct=37.5% |
| source_file字段 | ✅ 正确填充文件路径 |
| Markdown摘要生成 | ✅ 表格+统计摘要 |
| PostgreSQL入库 | ⚠️ PG服务未运行(已知阻塞) |

## 支持的JSON格式
1. **v3标准格式**: `{summary: {ic_mean, sharpe_ratio, ...}}`
2. **扁平格式**: `{total_return, sharpe_ratio, ...}` (字段在顶层)
3. **ic_result格式**: `{avg_ic, ic_std, ic_positive_pct, ...}`
4. **regime格式**: `{choppy.total_score_5d.ic, ...}` (部分兼容)

## 模块结构
- `find_result_files()` — 发现回测结果文件
- `load_result()` — 加载JSON
- `extract_metrics()` — 提取标准化指标(兼容4种格式)
- `ensure_table()` — 确保PG表存在
- `insert_result()` — 写入PG(去重)
- `generate_summary()` — 生成Markdown摘要
- `process_all()` — 一键处理所有结果

## 阻塞项
- PostgreSQL服务未运行，入库功能待PG恢复后验证
- 无新回测结果可测试端到端流程(需v3触发新回测)

## 记忆更新建议
- L3: 新增 backtest_result_parser.py (回测结果自动解析)
