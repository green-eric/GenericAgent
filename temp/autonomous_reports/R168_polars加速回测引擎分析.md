# Polars 加速回测引擎 — 可行性分析

> R169 | 2026-05-18 | 自主行动

---

## 结论：❌ 不推荐 polars 加速

**核心瓶颈是 SQLite I/O，不是计算引擎。**

---

## 性能基准测试

### 测试环境
- DB: stock_data.db (1398MB, 321.8万行 quotes)
- polars 1.40.1 | Python 3.12.10

### 读取 321 万行 quotes

| 方法 | 耗时 | 说明 |
|------|------|------|
| polars ODBC | 3698ms | ODBC 桥接效率低 |
| pandas→polars | 3524ms | pandas 读 + 转换开销 |
| pandas→polars (裁剪日期) | **144ms** | 只读需要的数据 |

### 计算 4344 只股票全程收益率

| 方法 | 耗时 | 说明 |
|------|------|------|
| 逐行 SQL (4344只) | **53ms** | 当前引擎方式，少量查询极快 |
| polars 向量化 | 549ms | 计算本身快，但读取慢 |
| pandas groupby | 714ms | 比 polars 慢 |
| Python dict 全量 | 4270ms | 最慢 |

---

## 关键发现

1. **逐行 SQL 在小批量场景极快** (20只×7期=1.6ms, 4344只=53ms)
   - SQLite 索引查询 O(log n)，4344 次查询 < 100ms
   - 当前引擎的 N+1 查询不是瓶颈

2. **polars/pandas 全量读取 321 万行需要 3.5 秒**
   - 即使计算快(500ms)，总耗时仍 > 4 秒
   - ODBC 读取 SQLite 效率极低

3. **真正的优化方向：批量 SQL + 日期裁剪**
   - `WHERE trade_date >= ? AND trade_date <= ?` 裁剪后读取仅 144ms
   - 预加载到内存 dict 后，后续查询 O(1)

---

## 推荐方案

| 场景 | 推荐方案 |
|------|----------|
| 少量股票查询 (< 100只) | 逐行 SQL（当前方式，已足够快） |
| 全量股票批量计算 | pandas read_sql 裁剪日期范围 → 计算 |
| 超大规模回测 | 预加载到内存 + dict 缓存 |

---

## 建议

⚠️ **polars 加速 TODO 标记为"不值得"**，因为：
- 当前引擎瓶颈不在计算，在 SQLite I/O
- polars ODBC 读 SQLite 比逐行 SQL 慢 70x
- 真正的优化是批量 SQL + 日期裁剪（可提速 25x）

如需进一步优化，建议：
1. 用 `WHERE trade_date` 裁剪 + pandas 批量读取
2. 或将 SQLite 数据预加载到内存 dict 缓存
