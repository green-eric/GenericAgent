# 自主行动 R284 — BfM SSE稳定性诊断建议

## 问题描述
- clash-verge 每日崩溃，port 7897 可用率仅 38%
- BfM 实时流 SSE 连接频繁断连

## BfM 项目结构
- 位置: D:\Project\BfM
- 架构: Vite+TS 前端 + Python 后端 (monitor.py)
- SSE 服务: modules/server.py (start_server/stop_streamer)
- 端口: 9004 (BfM 服务), 7897 (clash-verge 代理)

## 根因分析

### 1. clash-verge 崩溃 (主因)
- clash-verge 每日崩溃 → port 7897 不可用 → SSE 断连
- 可用率 38% 意味着每天约 14.8 小时不可用
- 可能原因: 内存泄漏、规则更新冲突、TUN 驱动不稳定

### 2. SSE 断连机制
- BfM monitor.py 有 stop_streamer() 和优雅关闭机制
- 但 clash-verge 崩溃是外部依赖，BfM 无法控制

## 建议修复方案 (需用户批准)

### P0: clash-verge 稳定性
1. 检查 clash-verge 日志找崩溃原因
2. 考虑更换为 clash-verge-rev 社区版 (更稳定)
3. 或配置 Windows 计划任务自动重启 clash-verge

### P1: BfM SSE 自动重连
1. 在 modules/server.py 中添加 SSE 断连自动重连
2. 指数退避重试 (1s/2s/4s/8s/16s/30s)
3. 心跳检测 (每 30s ping)

### P2: 监控告警
1. 在 daily_health_check.py 中添加 port 7897 检测
2. 不可用时自动推送微信告警

## 结论
TODO #4 需要用户介入处理 clash-verge 问题。BfM 端 SSE 自动重连可自主实现，但需用户批准后执行。
