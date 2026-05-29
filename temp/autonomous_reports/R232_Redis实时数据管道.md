# R232 | 能力 | Redis实时数据管道

## 结论
✅ **ga_redis_pipeline.py 创建完成** — pub/sub + stream + 消费者组 + 断线重连，全部功能验证通过。

## 延迟测试结果

| 测试项 | 平均 | P99 | 目标 | 状态 |
|--------|------|-----|------|------|
| 写入 (100次) | 0.85ms | 1.70ms | <100ms | ✅ PASS |
| 读取 (100次) | 1.46ms | 1.91ms | <100ms | ✅ PASS |
| 断线重连 | healthy | — | 自动恢复 | ✅ PASS |

**性能远超目标** — 实际延迟 < 2ms，比 100ms 目标快 50 倍。

## 模块结构

| 类 | 功能 |
|----|------|
| `RedisConnection` | 连接管理 + 断线重连 + 健康检查 |
| `MessageBus` | Pub/Sub 发布/订阅消息总线 |
| `DataStream` | Stream 数据流 + 消费者组 + ACK |
| `ScoreSysSignalPipeline` | 高级API：信号/因子/回测结果推送 |

## 预定义频道

- `channel:scoresys:signal` — 交易信号
- `channel:scoresys:factor` — 因子数据更新
- `channel:file_monitor:event` — 文件监控事件
- `channel:ga:task` — GA任务通知
- `channel:system:alert` — 系统告警

## 预定义数据流

- `stream:scoresys:ticks` — 行情tick数据
- `stream:scoresys:factors` — 因子计算结果
- `stream:backtest:results` — 回测结果流
- `stream:ga:events` — GA事件流

## CLI用法

```bash
# 延迟测试
python ga_redis_pipeline.py --test

# 健康检查
python ga_redis_pipeline.py --health

# 推送信号
python ga_redis_pipeline.py --push-signal 000001.SZ buy 10.5
```

## 环境信息
- Redis: 5.0.14.1 (Running, Auto-start)
- redis-py: 5.0.1
- 连接方式: 127.0.0.1:6379
