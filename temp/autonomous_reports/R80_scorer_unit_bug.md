# R80 — ScoreSys 四因子全50 bug 根因诊断报告

## 结论

**根本原因：DB 数据单位与 scorer 代码期望不一致（小数 vs 百分比）**

## 数据证据

| 字段 | DB 实际值 | 代码期望 | 影响 |
|------|-----------|----------|------|
| ret_5d | 0.693（=0.693%） | 百分比值（如 5.0 = 5%） | avg_ret≈0.005 → score≈50 |
| ret_10d | 0.345（=0.345%） | 百分比值 | 同上 |
| mom_1m | 0.043（=4.3%） | 百分比值（如 0.05=5%） | s1=50+0.043×2≈50 |
| turnover_5d | 0.0056（=0.56%） | 百分比值（2~8） | <2.0 → 过低分支 → score≈20~31 |
| ind_mom_1m | 0.015（=1.5%） | >0.05 判定热门 | 0.015<0.05 → cooling → score≈50 |

## 四因子计算复现

### momentum_score
    s1 = max(0.0, min(100.0, 50.0 + mom_1m * 2.0))
    # mom_1m=0.043 → s1 = 50 + 0.086 = 50.086 → round → 50

### industry_momentum_score
    # ind_mom_1m=0.015, 阈值 >0.05 判定热门
    # 0.015 < 0.05 → status='cooling' → score≈50

### reversal_score
    avg_ret = ret_5d * 0.6 + ret_10d * 0.4  # ≈ 0.005
    score = 50.0 - avg_ret * 3.0             # = 50 - 0.015 = 49.985 → 50
    # -5 < avg_ret < 5 → neutral → score≈50

### turnover_score
    # turnover_5d=0.0056, 代码期望 2~8
    # 0.0056 < 2.0 → 过低换手分支
    # score = 20 + 0.0056/2*40 = 20.11 → ~20
    # （如走路径2 ma20偏离度代理，可能得50）

## 修复方案（待批准）

**方案A（推荐）：scorer 入口统一乘100**
- reversal_score、momentum_score、industry_momentum_score、turnover_score 入口处将小数转百分比
- 改动小，风险低，约4处修改

**方案B：IndicatorCalculator 出口统一转百分比**
- 数据出口处统一转换，一劳永逸
- 更干净，但需确认所有下游消费者

## 影响范围

- 仅影响 scorer.py 中4个评分函数
- 修复后预期：分数范围 20~80，不再压缩在 50 附近
- 需重新运行回测验证 IC 改善

## 状态

🔴 待用户批准后执行修复
