# R190 | 2026-05-18 | 巡检 | 定时任务状态确认 + Redis实时数据深度探测

## 摘要
所有定时任务从未成功运行（LastRunTime全空），scores表仅5/15单天数据无新增。Redis实时数据丰富但行情仅39只(TTL 22s)。所有TODO仍需等待用户干预。

## 发现

### 🔴 定时任务全部未运行
| 任务名 | 状态 | LastRunTime | LastTaskResult |
|--------|------|-------------|----------------|
| RPS20_DailyBacktest | Ready | (空) | (空) |
| ScoreSys_DailyScore | Ready | (空) | (空) |
| ScoreSys-UpdateIndustryStats | Ready | (空) | (空) |

**原因**：计划任务需用户登录态才能触发，非交易日也不会执行。

### 📊 scores表状态
- 唯一日期: 2026-05-15 (4344只)
- 列名: id, symbol, calc_date, total_score, rating, growth, profitability, cash_flow, leverage, valuation, momentum, industry_momentum, reversal, turnover, market_regime, veto, veto_reason, created_at, confidence, data_completeness, raw_total_score, rank_score, score_basis
- 无新数据积累（R180-R183以来未变化）

### 🟢 Redis实时数据 (10716 keys)
| 数据类型 | 数量 | 说明 |
|----------|------|------|
| ashare:quote:v1 | 39 | 实时行情, TTL 22s, 含name/price/open/high/low/pct/vol/amount/turnover/market_cap/time |
| ashare:kline:v1 | 447 | K线数据, 约66个交易日(2026-02-02 ~ 2026-05-18) |
| ashare:earnings:forecast | 8470 | 财报预测, 含forecast_type(预增/略增/预减等) |
| ashare:earnings:announcement | 1244 | 财报公告, 含eps/revenue |
| ashare:news | 5 | 新闻数据 |
| bullish:market | 1 | 实时行情stream |

### 💡 Redis K线数据价值发现
- 447只股票有约66个交易日K线(日级别)
- 数据格式: [date, open, close, high, low, volume]
- **可用于短期动量因子计算**，补充SQLite quotes表

## TODO状态
- 🔴 P0: RPS20+ScoreSys融合策略参数优化 — 阻塞（需多日scores数据）
- 🟡 P1: scores表多日数据积累验证 — 阻塞（定时任务未运行）
- 🟢 P2: 已完成

## 建议
1. **下次交易日(5/19)用户在线时**：确认定时任务登录方式，手动触发一次ScoreSys_DailyScore
2. **Redis K线数据**：可考虑写一个短期动量因子计算脚本，利用Redis中447只股票的66日K线
3. **实时行情覆盖度低**：仅39只，可能是ws/stock系统订阅的活跃标的

## 记忆更新建议
- stock_data.db 正确路径: `D:\GenericAgent	emp\data\stock_data.db` (1398MB)，非 `temp\stock_data.db` (0MB)
- scores表日期列名: `calc_date`，非 `trade_date`
- Redis实时数据可用: 39只行情 + 447只K线 + 8470财报预测 + 1244财报公告
