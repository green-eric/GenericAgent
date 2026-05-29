# R248 | 融合选股实盘信号生成器

## 完成内容

创建 `live_signal_generator.py` — ScoreSys+BfM 融合选股实盘信号生成器

### 功能
- 从 ScoreSys stock_data.db 读取最新评分 + 行情数据
- 融合多维度因子生成实盘买入信号（评分+动量+行业热度+估值）
- 过滤涨停(>9.5%)/ST/科创板
- 输出JSON结构化数据 + Markdown可读报告
- 支持 `--min-score`/`--json-only` 等CLI参数

### 运行结果 (2026-05-22)
- 508条信号: 25只⭐重点推荐 + 483只👀观察
- 覆盖31个行业
- TOP重点: 康辰药业(73.5), 天秦装备(71.5), 东兴证券(70.4)

### Git
- commit: 84d40dc on master
- ScoreSys/live_signal_generator.py (271行)

### 验收标准检查
- [x] 从ScoreSys数据库读取评分+行情
- [x] 融合多因子(评分/动量/行业/估值)生成信号
- [x] 输出结构化JSON + MD报告
- [x] 过滤ST/涨停/科创板
- [x] CLI参数支持
- [x] git提交

## 记忆更新建议
- ScoreSys新增live_signal_generator.py (D:/Project/ScoreSys/live_signal_generator.py)
- 融合选股从回测(R156) → 实盘信号生成 (R248)
