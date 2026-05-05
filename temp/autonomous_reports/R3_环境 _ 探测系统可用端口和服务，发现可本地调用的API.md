# R03 - 探测系统可用端口和服务

> 自主行动产出 | 2026-05-04

## 摘要

扫描了localhost 60+个常见端口，发现**5个开放端口**和**7个Streamlit实例**等可交互服务，记录了服务端点和用途。

---

## 一、开放端口总览

| 端口 | 服务 | 进程 | 可交互 |
|------|------|------|--------|
| 53 | DNS代理 | verge-mihomo.exe (PID 7020) | DNS查询 |
| 445 | SMB | System (PID 4) | 文件共享 |
| 6379 | Redis | redis-server.exe (PID 6776) | ✅ 完全可用 |
| 18765 | TMWebDriver WS | pythonw.exe (PID 6932) | ✅ 浏览器控制 |
| 18766 | CDP Bridge | pythonw.exe (PID 6932) | ✅ 浏览器调试 |

---

## 二、可交互服务详解

### 1. Redis 6379 — ✅ 可用
- **进程**: redis-server.exe (PID 6776)
- **绑定**: 127.0.0.1:6379（仅本地）
- **验证**: PING → +PONG
- **用途**: 缓存、消息队列、状态存储
- **交互方式**: `redis-cli -h 127.0.0.1 -p 6379`

### 2. Streamlit 实例群 — 7个 ⚠️ 需进一步探测
- **端口**: 18518, 18520, 18530, 18543, 18557, 18560, 18572, 18575, 18591, 18594
- **进程**: pythonw.exe / python.exe（多个PID）
- **响应**: 全部返回 HTTP 200，body包含Streamlit版权声明
- **用途**: 数据可视化Web应用（可能是不同项目的dashboard）
- **注意**: 端口号不连续，说明是多次独立启动的

### 3. WorkBuddy WebUI 2529 — ✅ 可用
- **进程**: WorkBuddy.exe (PID 14276)
- **响应**: HTTP 200，返回HTML页面（中文界面，dark主题）
- **用途**: WorkBuddy桌面应用的Web界面

### 4. verge-mihomo 53/7897 — 代理/DNS
- **进程**: verge-mihomo.exe (PID 7020)
- **端口53**: DNS代理（响应DNS查询）
- **端口7897**: HTTP代理（返回400，需要正确的代理请求格式）
- **用途**: Clash系列代理工具，提供DNS和HTTP代理

### 5. clash-verge 33331 — 管理界面
- **进程**: clash-verge.exe (PID 10376)
- **响应**: HTTP 404（可能需要特定路径如 `/ui` 或 `/configs`）
- **用途**: Clash Verge的Web管理面板

### 6. TMWebDriver + CDP Bridge 18765/18766 — ✅ 可用
- **进程**: pythonw.exe (PID 6932)
- **端口18765**: TMWebDriver WebSocket
- **端口18766**: CDP Bridge（Chrome DevTools Protocol）
- **用途**: 浏览器自动化控制（已验证可用）

---

## 三、Python进程生态

发现**10+个Python进程**在运行，端口在18518-18594范围内，主要是Streamlit应用。这说明用户有多个数据项目在同时运行。

| PID | 端口 | 类型 | 进程 |
|-----|------|------|------|
| 16692 | 18518 | pythonw | Streamlit |
| 5136 | 18520 | pythonw | Streamlit |
| 2228 | 18530 | pythonw | Streamlit |
| 19484 | 18543 | python | Streamlit |
| 6932 | 18557, 18765, 18766 | pythonw | Streamlit + TMWD |
| 20568 | 18560 | python | Streamlit |
| 10620 | 18572 | pythonw | Streamlit |
| 18028 | 18575 | python | Streamlit |
| 19376 | 18591 | python | Streamlit |
| 20240 | 18594 | python | Streamlit |

---

## 四、系统服务端口（不可外部访问）

| 端口 | 服务 | 说明 |
|------|------|------|
| 135 | RPC | Windows RPC |
| 1026 | Service Control | Windows服务控制 |
| 1027 | Host Service | Windows主机服务 |
| 2179 | VMMS | 虚拟机管理服务 |
| 5040 | CDP | Windows CDP服务 |

---

## 五、关键发现

1. **Redis已运行且可用** — 可以直接用于缓存/消息队列
2. **7+个Streamlit实例** — 用户有多个数据项目在运行，端口18518-18594
3. **代理环境**: verge-mihomo + clash-verge 同时运行
4. **TMWebDriver/CDP Bridge正常工作** — 18765/18766端口已验证
5. **WorkBuddy有Web界面** — 端口2529
6. **无常见数据库**: MySQL(3306)、PostgreSQL(5432)、MongoDB(27017)均未运行
7. **无常见Web服务**: HTTP(80/443/8080)均未运行

---

## 六、建议

1. **Redis可立即使用** — 直接 `redis-cli` 连接，适合做缓存和状态存储
2. **Streamlit端口探测** — 可以进一步访问各端口查看具体是什么应用
3. **Redis未设置密码** — 仅监听127.0.0.1，安全性可接受
4. **多个Python进程** — 如果不需要，可以清理以释放资源
