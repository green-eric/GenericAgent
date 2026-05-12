# 2026-04-18 工作日志

## 微信 ClawBot 排查与修复

### 问题描述
用户报告微信 ClawBot 显示"连接中"或"已连接"，但无法在微信中收发信息，且出现 `command 'tencentcloud.codingcopilot.chat.sendMessage' not found` 错误。

### 排查过程
1. 检查了多次重启的日志（20260417T233716、20260418T150757、20260418T183225）
2. 15:08 的日志发现两个关键错误：
   - `[WeixinClient] getUpdates error (1/3): TypeError: fetch failed` - 长轮询获取消息失败
   - `Failed to start Centrifugo: net::ERR_TIMED_OUT` - Centrifugo 连接超时
3. 18:32 重启后：
   - Centrifugo 连接成功（`Connected successfully`）
   - 微信 ClawBot 重新扫码登录成功（botId=559d36baa4a4@im.bot）
   - 成功收到入站消息（18:34:44）
   - 成功发送回复消息（18:35:44）

### 最终状态
- ✅ 微信 ClawBot 已完全正常工作
- ✅ 消息收发正常
- ✅ Centrifugo 连接正常

### 根本原因
之前的问题是由于 Centrifugo 连接超时（网络问题）导致消息通道无法建立。重启后网络恢复正常，连接成功。
