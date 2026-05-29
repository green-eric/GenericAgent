# R103 | 2026-05-14 | 诊断 | ScoreSys reversal因子regime特异性分析

## 摘要
基于regime_ic_results.json（6个regime × 10个因子 × 3个持有期），分析reversal因子的regime特异性。**关键发现：reversal在crash_slow中极强(IC_5d=+0.4185)，在low_vol中极负(IC_20d=-0.2102)，regime特异性极强。**

## reversal因子 IC Regime矩阵

| Regime | 5日IC | 10日IC | 20日IC | 平均|IC| |
|--------|-------|--------|--------|---------|
| crash_slow | **+0.4185** | +0.1598 | +0.0340 | 0.2041 |
| crash_sharp | **+0.1629** | +0.0985 | +0.0634 | 0.1083 |
| trending | -0.0082 | -0.0423 | +0.0390 | 0.0298 |
| choppy | +0.0432 | -0.0132 | -0.0374 | 0.0313 |
| crash_sharp_bounce | -0.1280 | -0.1057 | -0.1243 | 0.1193 |
| low_vol | -0.0846 | -0.1963 | **-0.2102** | 0.1637 |

## 关键发现

### 🔴 强正IC场景：crash_slow（慢速下跌）
- 5日IC=+0.4185，极强！说明在慢速下跌市中，reversal因子选股能力极强
- 逻辑：慢速下跌中，超跌反弹效应显著，反转策略最有效
- 10日IC衰减至+0.1598，20日IC仅+0.0340 → **短期信号，衰减极快**

### 🔴 强负IC场景：low_vol（低波动）
- 20日IC=-0.2102，极强负信号
- 逻辑：低波动市中反转因子发出错误信号 → 应**反向使用**或**降权至0**
- 5日IC=-0.0846也显著为负 → 全周期负IC

### 🟡 正IC场景：crash_sharp（急跌）
- 5日IC=+0.1629，中等正IC
- 急跌中反转因子也有效，但不如crash_slow

### 🟢 中性场景：trending / choppy
- trending中20日IC=+0.0390（微弱正）
- choppy中IC在±0.04间震荡
- 这两个regime下reversal几乎无效

### ⚪ 负IC场景：crash_sharp_bounce（急跌反弹）
- 全周期负IC（-0.10 ~ -0.13）
- 急跌反弹市中reversal给出反向信号

## 对比其他因子

**trending regime 20日IC排名：**
1. valuation +0.0648
2. industry_momentum +0.0588
3. profitability +0.0484
4. **reversal +0.0390** ← 中等
5. momentum +0.0192

**low_vol regime 20日IC排名：**
1. growth +0.1084
2. valuation +0.1081
3. cash_flow +0.0499
...
8. industry_momentum -0.1879
9. **reversal -0.2102** ← 倒数第二，极负

## 假设验证

| 假设 | 验证结果 |
|------|---------|
| reversal在趋势行情中正IC | ❌ trending中IC≈0，几乎无效 |
| reversal在震荡市中负IC | ⚠️ choppy中IC≈0，low_vol中强负 |
| reversal在下跌市中有效 | ✅ crash_slow中极强(+0.42)，crash_sharp中正IC |

## 建议

1. **regime-specific权重**：crash_slow中reversal权重×2，low_vol中权重归零或反向
2. **crash_slow检测**：该regime下reversal是王者因子，应优先识别
3. **low_vol保护**：low_vol中reversal负IC显著，应避免在该regime下使用
4. **持有期**：reversal信号集中在5日，长期衰减快，适合短周期评分
