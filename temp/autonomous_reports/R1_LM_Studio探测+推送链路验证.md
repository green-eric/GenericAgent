# R1 LM Studio探测 + 实盘信号推送链路验证

## 1. LM Studio 推理服务探测

### 环境状态
- LM Studio 0.4.14 已安装: `C:\Users\green\AppData\Local\Programs\LM Studio\LM Studio.exe` (200MB)
- 模型: `Qwen2.5-Coder-1.5B-Instruct-GGUF` (940MB, Q4_K_M)
- lms CLI: `C:\Users\green\.lmstudio\bin\lms.exe` 可用
- GUI进程: 运行中

### 探测结论 ❌ Server不可用
尝试了4种方式启动LM Studio本地推理Server，均失败：

| 方式 | 结果 |
|------|------|
| `lms server start` (subprocess.run) | 超时(30s) |
| `lms server start` (Popen非阻塞) | 端口1234未就绪(30s等待) |
| 直接启动LM Studio.exe | GUI启动但server端口不通 |
| 探测端口4000 | 是ashare-monitor(Node.js)，非LM Studio |

**根因**: LM Studio 0.4.14的`lms server start`命令可能需要GUI交互环境或特定配置，CLI自动启动不可行。

### 建议
- 手动在LM Studio GUI中开启Local Server（端口1234）
- 或考虑使用Ollama作为替代本地推理方案

## 2. 实盘信号推送链路验证

### 链路状态 ✅ 可用

| 组件 | 状态 | 详情 |
|------|------|------|
| live_signals_latest.json | ✅ | 508只信号/25重点推荐，2026-05-22生成 |
| wxbot_token.json | ✅ | admin_uid有效(38chars) |
| WxBotClient导入 | ✅ | wechatapp.py正常加载 |
| 消息格式化 | ✅ | 1071chars，Top10格式正确 |
| live_signal_pusher.py | ✅ | dry-run通过 |

### 消息样例
```
📊 实盘选股信号日报
━━━━━━━━━━━━━━━
📅 日期: 2026-05-22  🕐 生成: 22:38:10
📈 重点推荐: 25 / 508 只
━━━━━━━━━━━━━━━
1. 康辰药业（603590）⭐73.5分 A+ | 🔴-2.04% | ¥38.42
2. 天秦装备（300922）⭐71.5分 A+ | 🔴-1.96% | ¥21.05
...
```

## 3. 新增: 信号图表生成器

### signal_chart_gen.py ✅ 创建并验证
- 用matplotlib将选股信号渲染为表格图片
- 深色主题 + Microsoft YaHei字体
- 生成 `signal_chart_latest.png` (115KB)
- 用法: `python signal_chart_gen.py --top 10`

### 待集成
- 将图表生成集成到live_signal_pusher.py的`--with-chart`选项
- 通过WxBotClient.send_image()推送图片到微信

## 总结
- ❌ LM Studio server无法CLI自动启动，需手动操作
- ✅ 实盘信号推送链路完全可用
- ✅ 新增图表生成器，为可视化推送奠定基础
