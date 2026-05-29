# ScoreSys 项目全景文档
> 生成时间: 2026-05-18 R176
> 验收: 1份ScoreSys项目全景文档(架构图+数据流+因子说明+API索引)

## 🏗️ 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     ScoreSys 评分系统                        │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ 数据采集  │ 因子计算  │ 评分引擎  │ 回测验证  │  输出/推送      │
│          │          │          │          │                 │
│ quotes   │ 9因子    │ 加权求和  │ IC回测   │ scores表        │
│ financials│ 行业中性 │ 否决机制  │ 组合回测  │ _score_cache    │
│ stocks   │ 标准化   │ 置信度   │ 参数优化  │ 微信推送        │
└──────────┴──────────┴──────────┴──────────┴─────────────────┘
```

## 🗄️ 数据库架构

### 表清单 (7个)

| 表名 | 行数 | 用途 | 关键字段 |
|------|------|------|----------|
| **quotes** | 321万 | 行情数据 | trade_date, close_price, volume, pe_ttm, total_mv, ret_*, mom_*, industry_mom_*, ma_* |
| **financials** | 19万 | 财务数据 | revenue, net_profit_parent, ocf, capex, total_assets, total_liab |
| **stocks** | 4344 | 股票基本信息 | symbol, name, industry, market, list_date |
| **scores** | 4344 | 评分结果 | total_score, rating, growth, profitability, cash_flow, leverage, valuation, momentum, industry_momentum, reversal, turnover, market_regime, veto |
| **_score_cache** | - | 评分缓存 | symbol, score, confidence, calc_date, market_regime, reversal, turnover |
| sqlite_sequence | 3 | 自增序列 | - |
| sqlite_stat1 | 17 | 查询统计 | - |

### ER 关系

```
stocks.symbol ──┬── quotes.symbol
                ├── financials.symbol
                ├── scores.symbol
                └── _score_cache.symbol
```

## 📊 9 因子详解

| # | 因子 | 字段来源 | 方向 | avg\|IC\| | 说明 |
|---|------|----------|------|-----------|------|
| ① | **momentum** | quotes.mom_1m | 正向 | 0.134 | 1月动量，最强因子 |
| ② | **reversal** | quotes.ret_5d | 反向 | 0.121 | 5日反转 |
| ③ | **turnover** | quotes.turnover_5d | 反向 | 0.121 | 5日换手率 |
| ④ | **industry_momentum** | quotes.industry_mom_1m | 正向 | 0.120 | 行业动量 |
| ⑤ | **valuation** | quotes.pe_ttm | 反向 | N/A(早期缺失) | PE估值倒数 |
| ⑥ | **size** | quotes.total_mv | 正向 | N/A(早期缺失) | 市值对数 |
| ⑦ | **growth** | financials.revenue | 正向 | 待测 | 营收增长 |
| ⑧ | **profitability** | financials.net_profit | 正向 | 待测 | 盈利能力 |
| ⑨ | **cash_flow** | financials.ocf | 正向 | 待测 | 经营性现金流 |

## 🔄 数据流

```
行情采集 ──→ quotes表 ──┐
                        ├──→ 因子计算 ──→ 标准化 ──→ IC加权 ──→ scores表
财务采集 ──→ financials ──┘                  │
                        ┌─────────────────────┘
                        ▼
                  回测验证 (IC / 组合收益)
                        │
                        ▼
                  微信推送 / 缓存
```

## 📁 脚本索引

### 核心脚本

| 脚本 | 用途 | 状态 |
|------|------|------|
| `ic_test_v2.py` | IC 回测（6因子，纯quotes） | ✅ 可用 |
| `ic_test_from_raw.py` | IC 回测（9因子，含financials） | ⚠️ JOIN需修复 |
| `rps20_scoresys_backtest.py` | RPS20×ScoreSys融合回测 | ✅ 可用 |
| `rps20_fusion_picker.py` | RPS20选股器 | ✅ 可用 |
| `factor_combination.py` | 因子组合优化 | ✅ 可用 |
| `grid_search_fusion.py` | 网格搜索参数优化 | ✅ 可用 |
| `regime_ic_*.py` | 市场状态IC分析系列 | ✅ 可用 |
| `backtest_engine.py` | 通用回测引擎 | ✅ 可用 |
| `ic_weighted_factor_test.py` | IC加权因子测试 | ✅ 可用 |

### 辅助脚本

| 脚本 | 用途 |
|------|------|
| `db_field_audit.py` | DB字段审计 |
| `scheduled_backtest.py` | 定时回测 |
| `kline_chart.py` | K线图生成 |
| `score_bfm_fusion.py` | ScoreSys+BfM融合 |

## 📈 回测结果摘要

| 指标 | 值 |
|------|-----|
| 数据范围 | 2023-04-10 ~ 2026-05-15 (749交易日) |
| 平均 avg\|IC\| | **0.0825** (验收标准: 0.035) ✅ |
| 等权组合 avg\|IC\| | 0.1219 |
| IC加权组合 avg\|IC\| | 0.1244 |
| 最强因子 | mom_1m (0.134) |

## ⚠️ 已知问题

1. **scores表覆盖率低**: 仅 41/431 只 RPS20 股票有评分（9.5%），仅1天数据
2. **财务因子未回测**: growth/profitability/cash_flow 因 financials JOIN 问题未纳入
3. **早期数据缺失**: 2023-04 前 pe_ttm/total_mv 几乎全空
4. **size/val_pe IC**: 早期数据不足导致 N/A
