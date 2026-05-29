# 自主行动 R285 — BfM SSE架构深度分析

## 分析范围
BfM (D:\Project\BfM) — SSE 服务端实现架构分析

## SSE 服务端架构

### 文件结构
- server.py (39KB) — HTTP服务器入口，/api/stream SSE端点 (line 338)
- sse_client_manager.py (4.5KB) — 客户端连接管理器（全局单例）
- pipeline_manager.py (86KB) — get_event_bus/get_sse_manager 全局单例
- controllers.py (39KB) — 业务控制器
- scoresys_bridge.py (20KB) — ScoreSys 数据桥接
- event_bus.py (9KB) — 事件总线（streaming/）

### SSE 连接流程
1. 客户端 GET /api/stream -> _handle_sse_stream()
2. 响应头: text/event-stream; charset=utf-8
3. 注册到 SSEClientManager（心跳60s, 最大100连接）
4. 发送 connected 事件 + 立即推送 ScoreSys 评分
5. 订阅 EventBus 持续推送行情/新闻/信号

### 已实现功能
- 客户端注册/注销 + 心跳检测
- 多客户端并发安全（threading.Lock）
- 连接数上限 100
- 心跳超时自动清理（60s）
- 新连接立即推送评分（解决一次性事件丢失）
- force_refresh 速率限制（30s 冷却）

## TODO #4 根因结论

BfM SSE 服务端实现已完善。clash-verge 每日崩溃导致 port 7897 可用率 38% 是网络环境问题，非代码 bug。

### 建议方案
1. [P0 用户处理] 修复 clash-verge 崩溃 / 升级 clash-verge-rev
2. [P1 可自主] 前端 SSE 自动重连（指数退避 1s->30s）
3. [P2 可自主] daily_health_check.py 添加 port 7897 代理检测
