# R97 | 2026-05-12 | 分析 | AlphaTrading因子与ScoreSys互补性深度分析

## 摘要
对 lca-123/alphas 仓库的274个因子（Alpha101: 83个 + Alpha191: 191个）按数据维度分类，识别出与ScoreSys 9因子互补的候选因子。

## ScoreSys现有9因子覆盖维度
| 因子 | 维度 |
|------|------|
| momentum | 价格动量(close delay/delta) |
| industry_momentum | 行业动量 |
| reversal | 价格反转(close vs MA) |
| turnover | 换手率(turnover/volume) |
| profitability | 盈利能力(财务) |
| growth | 成长性(财务) |
| cash_flow | 现金流(财务) |
| leverage | 杠杆(财务) |
| valuation | 估值(财务) |

**覆盖维度**: 价格动量、价格反转、成交量、财务指标
**缺失维度**: 波动率(STD)、价量相关性(CORR)、量价时序模式、极值统计

## Alpha191因子维度分类（191个）

### ① 波动率类(STD+价格) — 32个 [⭐最互补]
alpha#004,010,012,023,042,049,050,051,054,055,063,067,076,078,079...
- 计算方式: STD(CLOSE,N) / SMA + 条件波动率
- **ScoreSys完全没有波动率维度**
- 推荐: alpha#010(下行波动率), alpha#067(RSI类), alpha#023(上涨波动率)

### ② 价量关系类(VOL+PRICE+CORR) — 61个 [⭐互补]
alpha#001,005,007,009,011,025,029,032,033,035,039,040,043,044,045...
- 计算方式: CORR(RANK(DELTA(LOG(VOLUME))), RANK((CLOSE-OPEN)/OPEN))
- ScoreSys的turnover仅用volume/流通盘，缺少价量相关性
- 推荐: alpha#001(量价背离), alpha#034(均线偏离度)

### ③ 动量/延迟类(PRICE+DELAY) — 41个
alpha#003,014,015,018,019,020,022,024,026,027,030,037,052,053,058...
- 与ScoreSys momentum部分重叠，但周期参数不同
- 可作为动量因子的多周期补充

### ④ 纯成交量类 — 12个
alpha#016,036,080,081,090,097,100,102,121,145,155,168...
- 与ScoreSys turnover部分重叠

## 推荐移植清单（Top 5）

| 优先级 | 因子 | 维度 | 推荐理由 |
|--------|------|------|----------|
| P1 | alpha#010 | 下行波动率 | ScoreSys无波动率维度，下行风险预测强 |
| P1 | alpha#067 | RSI动量 | 经典技术指标，与momentum互补 |
| P1 | alpha#001 | 量价背离 | 价量相关性是ScoreSys盲区 |
| P2 | alpha#023 | 上涨波动率 | 非对称波动率，牛市信号 |
| P2 | alpha#034 | 均线偏离度 | 简单有效，12日均线/收盘价 |

## 移植工作量评估
- 每个因子移植到scorer.py约需30分钟
- 5个因子 ≈ 2.5小时
- 需修改: scorer.py(因子计算) + scoring.yaml(权重配置)
- **需用户批准后执行**（修改核心代码库）

## 下一步
1. 用户批准移植清单
2. 修改scorer.py添加5个因子
3. 修改scoring.yaml配置权重
4. IC回测验证新因子有效性
5. 如IC>0.03，加入正式因子集
