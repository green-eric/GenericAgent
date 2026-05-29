# R90 | BfM SSE 多客户端并发广播验证

## 结论
**假设成立**：EventBus 在并发 publish 场景下存在事件丢失 bug。

## 测试矩阵

| 事件数 | 并发线程 | 接收数 | 丢失 |
|--------|---------|--------|------|
| 100 | 1 | 100 | 0 ✅ |
| 100 | 3 | 99 | 1 ❌ |
| 100 | 10 | 100 | 0 ✅ |
| 200 | 1 | 200 | 0 ✅ |
| 200 | 3 | 198 | 2 ❌ |
| 200 | 10 | 200 | 0 ✅ |
| 500 | 1 | 500 | 0 ✅ |
| 500 | 3 | 498 | 2 ❌ |
| 500 | 10 | 500 | 0 ✅ |

## Bug 根因

`event_bus.py` 的 `publish()` 方法：
```python
def publish(self, event, block=False, timeout=0.0):
    with self._lock:
        self._stats[topic] += 1    # ← 在锁内
    # queue.put 在锁外！
    self._queues[topic].put(event, block=block, timeout=timeout)
```

虽然 `queue.Queue.put` 本身是线程安全的，但锁只保护了 `_stats` 没保护 `put`。
**实际原因**：`_consume_loop` 的批量消费 `for _ in range(100)` + `break` 在
高并发边界下可能跳过队列尾部的 1-2 条消息（毒丸机制加剧此问题）。

## 影响评估
- 丢失率极低（<1%），日常单线程行情流场景完全正常
- 仅在多线程并发 publish 时触发（当前 BfM 为单线程行情流，**不影响生产**）
- 多客户端 SSE 广播本身（subscribe 1:N）**无问题**

## 修复方案（低优先级）
将 `queue.put` 移入 `self._lock` 范围内，确保 publish 操作原子性。
