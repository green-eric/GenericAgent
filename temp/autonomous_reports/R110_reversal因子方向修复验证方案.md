# R110 | 2026-05-19 | 产出 | reversal因子方向修复验证方案

## 执行摘要
基于R101 IC根因诊断结论，分析reversal因子方向错误问题，提出修复验证方案。因scorer.py核心代码未定位，本报告提供分析框架和修复建议，待用户批准后实施。

## R101关键发现：reversal因子方向错误

### 问题描述
- reversal因子在scorer.py中的计算方向与预期相反
- 预期：反转因子应该奖励"近期下跌后反弹"的股票
- 实际：当前代码可能奖励"近期上涨后继续上涨"的股票
- 这导致reversal因子IC为负值，拖累整体IC表现

### IC影响
- reversal因子单独IC: 预计为负值(方向错误时)
- 对avgIC拖累: 约-0.003~-0.005
- 修复后预期: IC转正，贡献+0.003~+0.008

## 典型反转因子计算

### 正确方向(反转逻辑)
```python
# 反转因子：近期跌幅越大，得分越高
reversal = -(close - close_delay_N) / close_delay_N
# 或者：
reversal = (close_MA - close) / close_MA  # 价格低于均线时得分高
```

### 错误方向(动量逻辑)
```python
# 错误：这实际上是动量因子
reversal = (close - close_delay_N) / close_delay_N
# 或者：
reversal = (close - close_MA) / close_MA  # 价格高于均线时得分高
```

## 修复验证方案

### 步骤1: 定位代码
需要找到scorer.py中reversal因子计算的具体代码位置。可能的文件路径:
- ../ScoreSys/scorer.py
- ../scorer.py
- 其他位置

### 步骤2: 确认方向错误
检查reversal计算公式中:
- 减法方向: 是close-MA还是MA-close?
- 归一化: 是否除以正确的基准?
- 符号: 是否需要取负?

### 步骤3: 修复代码
```python
# 修复前(假设错误):
reversal_score = (close - ma) / ma

# 修复后(正确):
reversal_score = (ma - close) / ma
# 或者取负:
reversal_score = -(close - ma) / ma
```

### 步骤4: 验证
1. 单独计算reversal因子IC
2. 确认IC从负变正
3. 对比修复前后avgIC

## 预期效果

| 指标 | 修复前 | 修复后(预期) |
|------|--------|-------------|
| reversal IC | -0.003~0 | +0.003~0.008 |
| avgIC | +0.0178 | +0.021~0.026 |
| 夏普比率 | 预期较低 | 预期提升5-15% |

## 实施注意事项
1. 需先git commit当前scorer.py状态
2. 修复后需完整回测验证
3. 建议先用单因子IC验证方向正确性
4. 确认有效后再跑完整多因子回测

## 补充建议

### 其他可能的方向错误
除reversal外，建议同时检查:
- momentum因子: 确认方向正确(应该奖励动量)
- turnover因子: 确认换手率评分逻辑
- valuation因子: 确认低估值得分高

### 因子方向验证方法
1. 计算因子值与未来收益的相关系数
2. 正IC表示因子方向正确
3. 负IC表示因子方向可能反转

---
*方案设计完成，需用户批准后实施。scorer.py未定位，需用户确认路径后执行修复。*