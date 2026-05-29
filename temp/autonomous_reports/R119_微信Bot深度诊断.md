# 微信Bot诊断报告 — 用户离开期间自主探测

**时间**: 2026-05-14 19:07:11  
**背景**: 用户多次反馈"发消息没回复"，之前多次修复均未根治，用户要求彻底修好

---

## 已确认事实

| 项目 | 状态 | 说明 |
|------|------|------|
| bot进程 | ✅ 运行中 | get_updates 已调用108轮 |
| get_updates errcode | ✅ 全部为0 | token对get_updates有效 |
| 收到消息数 | ❌ 0条 | _on_message从未被调用 |
| sendmessage(错误Header) | ❌ errcode=-14 | 用的是ILINK/ILINK-App-Id格式（错误） |
| sendmessage(正确Header) | ⏳ 超时 | 网络超时，非token问题 |

## 关键发现

**之前所有外部sendmessage测试结论都是错误的！**

bot `_post()` 实际用的Header格式：
```
Authorization: Bearer {bot_token}
AuthorizationType: ilink_bot_token
ILINK-App-Id: bot
```

之前测试用的是 `Authorization: ILINK xxx` / `AuthorizationToken: xxx` 等错误格式，导致一直返回-14。

## 根因分析

**token可能没有过期**（get_updates正常工作证明token有效）

真正问题可能是：
1. **用户发消息的入口不对** — 消息没有路由到这个bot
2. **bot的get_updates收到了消息但解析失败** — 需要检查消息解析逻辑
3. **网络问题** — sendmessage超时（代理不稳定）

## 待验证（用户回来后）

1. **确认微信端发消息入口** — 用户是在哪个聊天窗口发的消息？
2. **用正确Header+大timeout测试sendmessage** — 确认发送通道是否正常
3. **检查get_updates消息解析逻辑** — 看是否有消息但解析失败
4. **可能需要重新登录** — 如果确认入口正确但仍收不到消息

## 教训

- ❌ 不要再用错误Header格式测试API
- ❌ 不要再说"修复好了"而没有端到端验证
- ❌ 不要再说"token过期"——get_updates正常证明token有效
- ✅ 需要用户确认微信端发消息入口
