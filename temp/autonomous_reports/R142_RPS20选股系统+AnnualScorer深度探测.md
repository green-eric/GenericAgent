# R143 | 探测 | RPS20选股系统 + AnnualScorer 深度探测

**时间**: 2026-05-15 | **类型**: 探测

---

## 1. RPS20 通达信板块文件

**位置**: `D:\Programs\zd_gyzq_gm\T0002\blocknew\`

| 文件 | 大小 | 说明 |
|------|------|------|
| `RPS2090.blk` | 3,879 bytes | 股票列表（纯文本，每行一个代码） |
| `RPS2090.dat` | 34,480 bytes | 二进制数据（含RPS强度值等） |

**blk文件内容**: 约 380+ 只股票代码（000/002/003/300/301/302/600/603/605开头），每行一个代码，无名称。

**dat文件**: 二进制格式，每只股票约 92 字节记录，包含：
- 股票代码（BCD编码）
- RPS强度值（float32，如 `H��A` = 约 17.0）
- 交易所标识（0=深圳, 1=上海）

**结论**: 这是用户在同花顺/通达信中手动创建的 RPS20 相对强度选股板块。RPS20 = 20日相对价格强度，是动量策略的经典指标。与 ScoreSys 的截面评分形成互补——RPS20 捕捉短期动量，ScoreSys 捕捉基本面质量。

---

## 2. AnnualScorer 项目

**位置**: `D:\Project\AnnualScorer\`
**版本**: v6.3.0
**定位**: 基于年报的多维度财务指标评分系统

### 2.1 与 ScoreSys 对比

| 维度 | ScoreSys | AnnualScorer |
|------|----------|-------------|
| 评分因子 | 12因子（截面归一化） | 4维度6指标（年报原文） |
| 数据源 | akshare 实时行情 + SQLite | NeoData API + akshare |
| 评分频率 | 日频 | 年频（年报发布后） |
| 行业处理 | 统一评分 | 同行业百分位排名 |
| 输出 | Excel + SQLite | Excel |
| 股票池 | 4344只（stock_data.db） | 4344只（xuan.txt） |
| 特殊处理 | VETO规则/金融股豁免 | 金融股特殊权重/亏损惩罚 |

### 2.2 核心架构

```
xuan.txt → annual_scorer.py → fetcher → NeoData API
                              → industry → 6级行业判定
                              → scorer → numpy 向量化评分
                              → exporter → Excel
```

### 2.3 评分模型

**四维权重**:
- 盈利能力 40%: ROE×0.4 + 毛利率×0.3 + 净利率×0.3
- 成长性 30%: 营收同比×0.4 + 净利润同比×0.6
- 现金流 20%: OCF/净利润×1.0
- 偿债风险 10%: 资产负债率（反向）

**特色**: 同行业百分位排名、亏损惩罚、完整度折扣、金融股特殊适配

### 2.4 关键文件

| 文件 | 大小 | 职责 |
|------|------|------|
| annual_scorer.py | 16KB | CLI入口/流程编排 |
| api_client.py | 9KB | NeoData API 调用/限流/重试 |
| fetcher.py | 9KB | 批量调度/缓存判断 |
| scorer.py | 13KB | 四维加权评分 |
| industry.py | 12KB | 6级行业判定 |
| parser.py | 8KB | 年报段落提取/正则解析 |
| db.py | 8KB | SQLite WAL 缓存 |
| exporter.py | 7KB | Excel 报告 |
| config.py | 3KB | 全局配置 |
| xuan.txt | 89KB | 4344只股票列表 |

### 2.5 数据库

- `stock_cache.db` (2MB): NeoData API 缓存
- `annual_scorer.db` (24KB): 评分结果

---

## 3. xuan.txt 观察列表

**位置**: `D:\Project\AnnualScorer\xuan.txt`
**规模**: 4344 行，覆盖全市场
**格式**: `代码 名称`（如 `600000 浦发银行`）
**范围**: 600000-302132（含主板/创业板/科创板/北交所）

**用途**: AnnualScorer 的输入股票池，与 ScoreSys 的 stock_data.db 覆盖范围一致。

---

## 4. 发现与建议

### 🔍 关键发现

1. **两套系统互补**: ScoreSys（日频12因子）和 AnnualScorer（年频4维度）可融合为"动量+基本面"双轮驱动
2. **RPS20 动量数据**: 通达信板块文件包含 380+ 只 RPS20 强势股，可作为 ScoreSys 的动量预筛选
3. **NeoData API**: AnnualScorer 使用 NeoData 作为年报数据源，ScoreSys 可借鉴其年报解析能力
4. **xuan.txt 共享**: 4344只股票列表可在两系统间共享，避免重复维护

### 💡 后续建议（需用户批准）

1. **融合选股**: 将 RPS20 动量预筛选 + ScoreSys 基本面评分 + AnnualScorer 年报评分三者融合
2. **NeoData 接入**: 评估 NeoData API 的稳定性和成本，考虑引入 ScoreSys
3. **统一股票池**: 将 xuan.txt 与 stock_data.db 的股票列表同步机制建立起来

---

## 5. 环境信息

- **Python**: ≥ 3.10
- **NeoData Token**: `~/.workbuddy/.neodata_token`（需用户配置）
- **依赖**: akshare, numpy, openpyxl, sqlite3
