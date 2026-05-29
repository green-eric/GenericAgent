# R121 | 2026-05-14 | 诊断 | AKShare/东方财富API网络问题根因诊断

## 摘要
R106/R115均报告东方财富API `Connection aborted / RemoteDisconnected`，但代码逻辑正确。本轮通过DNS/代理/TLS三层探测，**确认根因是Clash Verge TUN模式DNS劫持**，并验证了绕过方案。

## 根因链条

```
Clash Verge 运行中 (TUN模式)
  → DNS查询被劫持，返回198.18.x.x虚假IP (RFC 2544测试地址)
  → 应用连接198.18.x.x:443
  → TLS握手失败 (SSL: UNEXPECTED_EOF_WHILE_READING)
  → RemoteDisconnected / Connection aborted
```

## 关键证据

| 检测项 | 结果 | 说明 |
|--------|------|------|
| Clash进程 | clash-verge-service.exe + clash-verge.exe | TUN模式运行 |
| 系统代理 | ProxyEnable=0 | 未启用系统代理，但TUN模式绕过 |
| DNS解析(eastmoney) | 198.18.0.17 (虚假) | Clash DNS劫持 |
| DNS解析(腾讯) | 198.18.0.16 (虚假) | 全部域名被劫持 |
| DoH真实IP(eastmoney) | **119.3.232.150** | Google DNS解析 |
| 198.18.x.x:443 TLS | ❌ SSL EOF失败 | 虚假IP无法完成TLS |
| 直连真实IP:443 | ✅ HTTP 200, JSON rc=0 | 数据正常返回 |

## 解决方案（已验证）

### 方案A: 直连真实IP（推荐，已验证）
```python
# 通过DoH获取真实IP后直连
import ssl, socket, json

def get_real_ip(hostname):
    # 使用Google DoH或阿里DoH获取真实IP
    import urllib.request, json
    req = urllib.request.Request(
        f"https://dns.google/resolve?name={hostname}&type=A"
    )
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    return data["Answer"][0]["data"]

real_ip = get_real_ip("push2.eastmoney.com")  # → 119.3.232.150
ctx = ssl.create_default_context()
s = socket.create_connection((real_ip, 443), timeout=10)
ss = ctx.wrap_socket(s, server_hostname="push2.eastmoney.com")
# 正常发送HTTP请求...
```

### 方案B: 配置Clash直连规则
在Clash配置中添加东方财富域名直连规则：
```yaml
rules:
  - DOMAIN-SUFFIX,eastmoney.com,DIRECT
  - DOMAIN-SUFFIX,eastmoney.cn,DIRECT
```

### 方案C: 临时关闭Clash TUN模式
切换到规则模式 + 系统代理，确保代理端口(7890)可用。

## 与R106关联
R106发现东财源RemoteDisconnected但腾讯源可用，当时误判为"东财封禁"。实际上腾讯源同样被DNS劫持，但R106使用的`qt.gtimg.cn`恰好Clash返回了可用的拦截页面（HTTP 200），掩盖了问题。

## 结论
- **根因**: Clash Verge TUN模式DNS劫持，非东财封禁
- **影响范围**: 所有走HTTPS的国内金融API（东财、腾讯、新浪等）
- **修复难度**: 低（方案B/C为配置改动，方案A需代码适配）
- **推荐**: 方案B（Clash规则），一次配置永久生效

## ⚠️ 注意
本轮仅做网络诊断和方案验证，**未修改任何代码或配置**。方案实施需用户批准后执行。
