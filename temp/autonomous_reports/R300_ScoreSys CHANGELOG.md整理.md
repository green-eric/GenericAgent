# R301 — ScoreSys CHANGELOG.md 整理

## 任务
TODO #4: ScoreSys changelog整理 — V15.2→V16.8跨越多个版本，CHANGELOG.md需系统性整理。

## 执行过程
1. 定位ScoreSys仓库：`D:\Project\ScoreSys`（通过es搜索`path:score`发现）
2. 扫描全量git log：43条commit
3. 提取关键版本commit的变更统计和日期
4. 读取README.md获取当前版本信息和回测数据
5. 按版本号倒序整理CHANGELOG.md

## 产出
- 新增 `CHANGELOG.md`（116行），覆盖 V15.2 → V16.8 完整版本演进时间线
- Git commit: `278bcd7` — `docs: 添加CHANGELOG.md — V15.2→V16.8完整版本演进时间线`

## 版本概要
| 版本 | 日期 | 关键变更 |
|------|------|----------|
| V16.8 | 2026-05-28 | 回测引擎7种模式、drawdown/benchmark分析、智能网络适配 |
| V16.0 | 2026-05-28 | long_term新增波动率+流动性因子 |
| V15.9 | 2026-05-26 | 回测+82.81%/夏普2.251/21因子 |
| V15.8 | 2026-05-26 | PCA权重归一化修复 |
| V15.7 | 2026-05-26 | PCA合成因子集成(PC1+PC2) |
| V15.5 | 2026-05-25 | GrowthScorer修复+换手率权重降低 |
| V15.3 | 2026-05-25 | 负IC因子归零+vol_squeeze清零 |
| V15.2 | 2026-05-25 | weight_optimizer系统性修复 |
| <V15.0 | 2026-05-22 | 实盘信号生成器+日检脚本+Soft Membership |

## 记忆更新建议
- ScoreSys仓库路径：`D:\Project\ScoreSys`（重要环境事实）
