# R277 — fusion_picker_v2.py 代码审查报告

> 审查时间: 2026-05-25  
> 文件: `D:\Project\ScoreSys\archive\fusion_picker_v2.py` (609行)  
> 审查人: GA 自主行动  

---

## 1. 可运行性验证

| 测试项 | 结果 | 备注 |
|--------|------|------|
| 语法检查 | ✅ 通过 | `py_compile` 无报错 |
| 运行测试 (skip-rps) | ✅ 通过 | 4344只股票全流程跑通, 耗时<1s |
| 默认参数运行 | ❌ 失败 | 默认DB路径 `archive/stock_data.db` 不存在 |
| JSON导出 | ✅ 通过 | `--json` / `--export` 正常 |
| 回测模式 | ⚠️ 未深度验证 | 框架存在但回测逻辑较简化 |

## 2. 架构评估

### 整体结构 (评分: 7/10)

```
load_rps20_codes()     → RPS20动量预筛选
ScoreSysReader         → 读取评分+行情数据 (SQLite)
BfMScorer              → 5维代理评分
FusionEngine           → 动态权重融合 + RPS bonus
run_backtest()         → 简化回测
display_results()      → 格式化输出
main()                 → CLI入口
```

**优点:**
- 模块化设计清晰, 数据读取/评分/融合/输出分离
- 支持 CLI 参数灵活配置 (regime/weights/RPS/dry-run/json)
- 有 RPS20 交集降级逻辑 (<20只自动降级全市场)
- 支持 JSON 导出, 便于下游消费

**问题:**

### 🔴 P0 — 必须修复

1. **默认DB路径错误** (L77附近 `DEFAULT_DB`)
   - 当前: `D:\Project\ScoreSys\archive\stock_data.db`
   - 应为: `D:\Project\ScoreSys\stock_data.db`
   - 影响: 不带 `--db` 参数直接运行必然崩溃

2. **`stocks` 表可能不存在** (ScoreSysReader L129)
   - `get_latest_scores()` 中 `LEFT JOIN stocks st ON st.symbol = sc.symbol`
   - 实际 `stock_data.db` 中无 `stocks` 表, 只有 `scores` 和 `quotes`
   - 当前能运行是因为 LEFT JOIN 不报错, 但 `name`/`industry` 字段全部为 NULL
   - 影响: 输出中股票名称全部为空

### 🟡 P1 — 建议修复

3. **Regime推断逻辑** — 当前推断为 `crash_sharp`
   - L557: `regime = reader.get_regime_from_scoresys() or "range"`
   - 从 `scores.market_regime` 读取, 最近日期全部为 `crash_sharp`
   - 需要确认: 这是真实市场状态还是 regime 判定逻辑有问题?
   - `crash_sharp` 权重: SS=50%, BfM=50%, 看起来合理

4. **BfM评分硬编码阈值** (BfMScorer L226-250)
   - PE-TTM 分档: `<15=100, <25=75, <40=50, <60=25, >=60=0`
   - MA均线判断: `ma5>ma10=25, ma10>ma25=25`
   - 这些阈值没有外部配置, 调参困难
   - 建议: 抽取为配置参数或 JSON 文件

5. **SQL注入风险** (ScoreSysReader L154)
   - `placeholders = ','.join(['?' for _ in symbols])` 使用参数化查询, ✅ 安全
   - 但 `f-string` 拼接 IN 子句, 如果 symbols 列表为空会生成 `IN ()` 语法错误
   - 建议: 增加空列表检查

6. **RPS20 文件格式假设** (load_rps20_codes L96-102)
   - 假设7位代码(第一位交易所标识), 但实际格式可能不同
   - 无格式校验, 解析失败时静默跳过
   - 建议: 增加格式校验和警告日志

### 🟢 P2 — 优化建议

7. **回测模块过于简化** (run_backtest L399-469)
   - 仅统计评级分布/平均分/行业分布/RPS命中率
   - 无净值曲线、无IC计算、无分组收益
   - 建议: 接入 ScoreSys 回测框架或输出到 R 回测脚本

8. **无异常处理**
   - 数据库连接无 try/finally (但有 close())
   - 无重试机制
   - 建议: 增加 DB 连接异常处理和重试

9. **日志级别不一致**
   - 大量 `logger.info`, 缺少 `logger.debug`
   - 建议: 详细日志改为 debug, 关键节点保留 info

10. **缺少单元测试**
    - BfMScorer/FusionEngine 可独立测试
    - 建议: 增加 pytest 测试用例

## 3. 代码质量评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 可读性 | 8/10 | 命名清晰, 注释充分, 结构合理 |
| 健壮性 | 5/10 | 缺少异常处理, 边界条件未覆盖 |
| 可维护性 | 6/10 | 硬编码阈值多, 配置化不足 |
| 性能 | 9/10 | SQLite + dict 查找, 4344只<1s |
| 可扩展性 | 7/10 | 模块化好, 但权重/阈值耦合 |
| **综合** | **7/10** | **可用, 需修复P0后投入实盘** |

## 4. 运行示例

```bash
# 正确运行方式 (需指定DB路径)
python archive/fusion_picker_v2.py --db D:\Project\ScoreSys\stock_data.db --skip-rps --dry-run --top 20

# JSON导出
python archive/fusion_picker_v2.py --db D:\Project\ScoreSys\stock_data.db --skip-rps --export result.json
```

## 5. 建议修复优先级

1. **立即**: 修复 DEFAULT_DB 路径
2. **立即**: 移除/替换 `LEFT JOIN stocks` (改用 quotes 表的 industry 字段)
3. **短期**: BfM 阈值配置化
4. **中期**: 增强回测模块
5. **长期**: 增加单元测试

---

*审查结论: 代码整体质量良好, 架构清晰, 性能优秀。修复2个P0问题后即可投入实盘使用。*
