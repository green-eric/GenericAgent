# BullishForMonitoring 实时流改造 SOP

## 分支
- 开发分支: `feature/stream-realtime`
- 验证通过后推 `master`

## 架构概览

```
东方财富SSE ──→ quote_streamer.py ──→ EventBus(market_data) ──→ MarketDataConsumer ──→ Redis Stream
                                                                       │
                                                                       ↓
                                                               EventBus(sse_broadcast) ──→ /api/stream ──→ 前端EventSource

新闻源 ──→ news_streamer.py ──→ EventBus(news) ──→ MarketDataConsumer ──→ Redis Stream
```

## 关键文件

| 文件 | 职责 |
|------|------|
| `modules/quote_streamer.py` | 东方财富SSE行情流，每只股票独立线程+指数退避重连 |
| `modules/news_streamer.py` | 新闻流实时化，替代scheduler定时缓存 |
| `modules/streaming/event_bus.py` | 事件总线，含SSE_BROADCAST事件类型 |
| `modules/streaming/consumer.py` | MarketDataConsumer，消费EventBus+写Redis |
| `modules/server/pipeline_manager.py` | start_streamer集成Streamer+Consumer+Redis |
| `modules/server/server.py` | /api/stream SSE端点，订阅EventBus推送给前端 |
| `modules/server/scheduler.py` | 废弃_news_cache_task |
| `src/ts/modules/sse.ts` | 前端SSEClient，EventSource+自动重连 |
| `src/ts/modules/app.ts` | Application集成SSEClient |
| `src/ts/modules/ui.ts` | updateQuoteRealtime/updateNewsRealtime/showSignalToast |
| `src/ts/types.ts` | MarketDataEvent/NewsEvent/SignalEvent/SSEEvent类型 |

## 数据源

### 东方财富SSE
- URL: `https://push2.eastmoney.com/api/qt/stock/sse?secid={secid}&fields={fields}`
- **必须加** `proxies={"http": None, "https": None}` 绕过本地代理（Clash等）
- headers: Referer=https://quote.eastmoney.com/, Origin, UA, Cache-Control=no-cache
- 502根因：本地代理(127.0.0.1:7897)拦截HTTPS，非API问题
- 备选: 腾讯API `http://qt.gtimg.cn/q=sz{code}`

### 字段映射
- f43=最新价(×100) f44=最高 f45=最低 f46=开盘 f47=成交量 f48=成交额
- f50=量比 f51=涨停价 f52=跌停价 f57=代码 f58=名称 f60=昨收 f170=涨跌幅(×100)
- 价格类字段需/100

## 启动流程

1. `python -m modules.server.server --port 8080`（Windows 8080可能被占用，换9090）
2. server.start_server() → 启动HTTP服务
3. server.serve_forever() → 阻塞监听
4. 后台线程调用 start_streamer()
5. start_streamer() → EventBus.start() → Streamer.start() → Consumer.start()

## 关键配置

| 参数 | 值 | 说明 |
|------|------|------|
| `EventBus.max_queue_size` | 20000 | pipeline_manager.py，防队列满丢事件 |
| `EventBus.num_workers` | 2 | 消费线程数 |
| `poll_interval` | 3.0s | quote_streamer 轮询间隔 |
| `max_symbols` | 100 | 种子池截取上限（全量526只） |
| `cache 单条限制` | 5MB | cache.py 中 Redis/内存缓存上限 |
| `scoring 线程池` | 4线程 | consumer.py 评分异步化 |
| `Redis批量写入` | 50条/1秒 | consumer.py 批量刷盘 |

## 常见坑

1. **EventType未导入**: server.py需`from modules.streaming.event_bus import EventType`
2. **代理拦截**: quote_streamer.py必须加proxies参数绕过本地代理
3. **sse.ts类型重复**: SSEEventType/SSEEvent定义在types.ts，sse.ts从types.ts导入
4. **start_streamer位置**: 必须在serve_forever()之后调用（后台线程）
5. **EventBus队列**: 消费循环用get_nowait()批量消费，禁get(timeout)轮询
6. **端口权限**: Windows 8080端口可能被占用(PermissionError 10013)，换其他端口
7. **队列溢出丢事件**: 若消费慢(scoring/Redis同步)会导致队列满丢事件，已改为异步评分+批量Redis写入

## Git

- 最新commit: 1e03592 (fix: EventBus队列+缓存+消费优化)
- 前一commit: cae3a18 (fix: 修复EventBus队列溢出丢事件 + 缓存项过大跳过)
- 前一commit: a631612 (fix: start_streamer各组件加独立try/except异常捕获)
- 分支: `feature/stream-realtime`
