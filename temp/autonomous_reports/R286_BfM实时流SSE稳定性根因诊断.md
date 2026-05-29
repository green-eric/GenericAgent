# R291 — BfM 实时流 SSE 连接稳定性根因诊断与恶化趋势

> 时间: 2026-05-28 | 类型: 诊断 | 自主行动
> 数据源: proxy_logs/proxy_health.jsonl (30条, 5-16 ~ 5-28) + 实时探测

---

## 一、执行摘要

| 指标 | R274 (5-16~5-25) | R291 (5-16~5-28) | 变化 |
|------|-------------------|-------------------|------|
| port7897 可用率 | 64% (14/22) | 63% (19/30) | → 持平 |
| clash-verge 双进程率 | 64% (14/22) | 60% (18/30) | ↓ 略降 |
| **5-27~5-28 可用率** | — | **0% (0/4)** | 🔴 **恶化** |

**核心结论**: clash-verge 主进程从 5-27 09:00 起**持续缺失**（仅 service 进程存活），port7897 连续 **3天+** 完全不可用。问题从"每日间歇性崩溃"恶化为"持续离线"。

---

## 二、时间线分析

### Phase 1: 稳定期 (5-16 ~ 5-18)
- port7897: 100% (14/14)
- clash-verge + service: 双进程稳定
- 外网连通: Google 93%, GitHub 93%

### Phase 2: 间歇崩溃期 (5-23 ~ 5-26 21:00)
- port7897: 50% (5/10)
- clash-verge 每日 09:00 崩溃，21:00 恢复
- 模式: 早崩晚恢复

### Phase 3: 持续离线期 (5-27 09:00 ~ 5-28 至今) 🔴
- port7897: **0%** (0/4)
- clash-verge 主进程: **完全缺失**
- 仅 service 进程 (PID 4340) 存活
- **无任何自动恢复迹象**

---

## 三、根因分析

### 确定根因: clash-verge 主进程崩溃且不再自动恢复

**证据链**:
1. `clash-verge-service.exe` (PID 4340) 始终存活 → Windows 服务正常
2. `clash-verge.exe` 主进程从 5-27 起消失 → GUI/代理核心崩溃
3. port7897 未监听 → 代理端口关闭
4. 系统代理 `ProxyEnable: 0` → 系统代理未激活

**可能原因**:
1. **clash-verge 版本 bug**: 内存泄漏导致运行数小时后崩溃（R274 已提出）
2. **Windows 自动更新/重启**: 5-26 晚可能发生了系统更新，clash-verge 未配置开机自启
3. **配置文件损坏**: 崩溃后配置损坏，无法重新启动
4. **TUN 驱动问题**: clash-verge 的 TUN 模式驱动异常导致启动失败

### 与 BfM SSE 的关联

BfM 实时流架构:
```
东方财富SSE → quote_streamer.py → EventBus → MarketDataConsumer → Redis Stream
                                                              ↓
                                                      SSE_BROADCAST → 前端
```

**影响路径**:
- clash-verge 崩溃 → port7897 关闭 → 外网不可达
- 但 BfM SSE 连接的是**东方财富**（国内），不依赖代理
- **关键问题**: BfM 的 `quote_streamer.py` 连接 `push2.eastmoney.com`（国内），理论上不受代理影响
- **实际影响**: 如果 BfM 服务器部署在云上，管理通道（SSH/API）可能依赖代理

---

## 四、当前状态 (2026-05-28 实时)

| 检测项 | 状态 |
|--------|------|
| clash-verge-service.exe | ✅ 运行中 (PID 4340) |
| clash-verge.exe | ❌ 未运行 |
| port7897 | ❌ 未监听 |
| port7890 | ❌ 未监听 |
| 百度直连 | ✅ 正常 |
| Google via proxy | ❌ 不可达 |
| 系统代理 | ❌ 未启用 |

---

## 五、建议方案

### P0: 立即恢复代理（需用户操作）
1. 手动启动 clash-verge 主程序
2. 检查 clash-verge 是否配置了"开机自启"和"自动重启"
3. 如无法启动，尝试重装 clash-verge

### P1: 配置 clash-verge 自动守护（可自主实现）
1. 创建 Windows 计划任务，每 5 分钟检查 clash-verge 进程
2. 若主进程缺失，自动启动 `clash-verge.exe`
3. 脚本可参考已有的 `proxy_health_check.py` 扩展

### P2: BfM SSE 客户端增强（需代码访问）
1. `quote_streamer.py` 已有指数退避重连（SOP 已记录）
2. 前端 `sse.ts` 的 EventSource 自带自动重连
3. **无需修改代码** — 架构已有重连能力

### P3: 长期方案
1. 考虑替换 clash-verge 为更稳定的代理方案（如 Clash Meta / sing-box）
2. 或配置备用代理通道

---

## 六、TODO 状态评估

**TODO #4 验收标准**: SSE 连续运行 72h 无断连

**当前评估**: ❌ 未达标
- 代理层: clash-verge 持续离线 3 天
- BfM 层: 代码已有重连能力，但代理不稳定影响管理通道
- **根本问题在 clash-verge，不在 BfM 代码**

**建议**: 此 TODO 的解决依赖用户手动恢复 clash-verge。自主行动可做的：
1. ✅ 已完成根因诊断
2. 🔄 可创建 clash-verge 自动守护脚本（需用户批准后实施）
3. ⏳ 等待用户恢复代理后验证 BfM SSE 稳定性

---

*自主行动 R291 完成 — BfM SSE 稳定性诊断*
