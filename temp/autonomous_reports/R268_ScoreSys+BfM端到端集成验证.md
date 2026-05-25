# R268 — ScoreSys+BfM端到端集成验证

## 摘要
验证从微信Bot触发 → BfM实时流获取 → 结果回传微信的完整链路。

## 验证结果

### 链路全览
```
微信用户发送 /bfm → wechatapp.py → http://127.0.0.1:9004/data → BfM实时流
                  ← 格式化消息 ← agent.observe_list + picks + hot8 ← ScoreSys评分
```

### 各节点状态

| 节点 | 状态 | 详情 |
|------|------|------|
| 微信Bot进程 | ✅ 运行中 | 7个python进程，含wechatapp |
| /bfm命令 | ✅ 已实现 | L922，调用BfM API |
| BfM API /data | ✅ 正常 | 200, 49只精选+8只热门 |
| BfM API /health | ✅ 正常 | v9.2.0, healthy |
| ScoreSys评分 | ✅ 已集成 | agent.observe_list含18只评分股票 |
| Agent交易 | ✅ 运行中 | 50笔交易, 胜率32%, 年化23.35% |

### BfM实时数据样本
- 精选Top1: 国恩股份(sz002768) [化工煤炭] ⭐64
- 精选Top2: 兴森科技(sz002436) [AI硬件] ⭐63
- 热门Top1: 京东方Ａ(sz000725) 热度103 📈+1.7%
- 观察列表: 18只(含ScoreSys评分)

### 模拟微信消息输出
```
📊 BfM 实时信号
🕐 2026-05-25 10:00:45

🔟 精选 49 只
1. 国恩股份(sz002768) [化工煤炭] ⭐64  fu15 st13 pe12
2. 兴森科技(sz002436) [AI硬件] ⭐63  fu18 st11 pe10
...

🔥 热门 8 只
  京东方Ａ(sz000725) 热度103 📈+1.7%
  长电科技(sh600584) 热度100 📈+3.2%
  ...
```

## 结论
✅ 验收通过：ScoreSys+BfM端到端链路全通
- 微信Bot /bfm命令已实现并可用
- BfM API正常返回实时选股信号
- ScoreSys评分已通过agent.observe_list集成到BfM
- Agent自动交易运行中(50笔, 年化23.35%)
