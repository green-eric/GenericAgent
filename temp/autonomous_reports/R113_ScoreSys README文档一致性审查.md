# R108 | 2026-05-13 | 优化 | ScoreSys README文档一致性审查

## 摘要
逐行审查README.md(887行) vs 实际代码(scorer.py/config.yaml/database.py/weight_optimizer.py)，发现多处文档与代码不一致。

## 📋 不一致清单（按严重度排序）

### 🔴 P0 — 数据层错误（影响使用）

| # | 位置 | README描述 | 实际代码 | 建议 |
|---|------|-----------|---------|------|
| 1 | 4.2.1 quotes表结构 | "最新交易日 `2026-05-11`" | DB当前为空(0行)，数据刷新中 | 等数据刷完后更新为实际最新日期 |
| 2 | 4.2.3 数据库总览 | quotes "938万行"、financials "19.4万行"、scores "4344行" | DB当前为空 | 数据全部过时，需等刷新后重新统计 |
| 3 | 3.1 快速开始 | "评分结果自动输出到 `scores_YYYYMMDD.xlsx`" | 实际文件名格式为 `评分结果_YYYYMMDD_HHMMSS.xlsx` | ✅ 代码正确，README需补 `_HHMMSS` |

### 🟡 P1 — 因子/权重描述不一致

| # | 位置 | README描述 | 实际代码 | 建议 |
|---|------|-----------|---------|------|
| 4 | 9. 配置说明权重表 | 12因子+3Alpha因子 | scorer.py只有10个因子方法(无alpha_xxx_score) | README超前，Alpha因子代码未实际接入scorer |
| 5 | 6.3.2 weight_optimizer | `regime_min_weight: 0.03` | weight_optimizer.py V1.1注释说"负IC因子获得最小权重 min_weight"，但代码V1.3.1修复说"负IC因子权重置0" | README参数表需更新，移除`regime_min_weight`或标注"已废弃" |
| 6 | 6.3.2 | `min_weight: 0.02` 标注"compute_weights参数" | 代码V1.3.1已改为负IC=0 | README需更新描述 |
| 7 | config.yaml | `alpha_vol_ratio: 0.05` | README 9节写 `alpha_volume_price: 5%` | 同一因子两个名字，需统一 |

### 🟢 P2 — 文档细节/过时描述

| # | 位置 | README描述 | 实际代码 | 建议 |
|---|------|-----------|---------|------|
| 8 | 6.3.5 | "V13.9.3起移除了AUTO_WEIGHT_MODE开关和REGIME_WEIGHTS" | ✅ 确认已移除 | 但6.3节还有"AUTO_WEIGHT_MODE已移除"的历史说明，可清理 |
| 9 | 4.2.2 scores表字段 | 列出 `cash_flow` 字段 | DDL中实际字段名是 `cash_flow` ✅ | 一致，无问题 |
| 10 | 5.1 main.py参数 | `--export` 标注"默认已启用" | 需确认代码中是否默认启用 | 待验证 |
| 11 | 6.1 backtest.py | `--mode` 参数重复两次 | 可能是文档排版问题 | 去重 |
| 12 | 11. 版本历史 | V13.10是最新版本 | config.yaml标注 V13.9.3 | 版本号不一致，需统一 |

## 📊 评分
- 文档完整度: 8/10 (覆盖全面但有过时数据)
- 文档准确度: 6/10 (多处与代码不一致)
- 建议优先修复P0和P1

## ⚠️ 注意
本轮仅做文档审查，**不修改任何代码**。修复需用户批准后执行。
