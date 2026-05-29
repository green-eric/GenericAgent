# R133 — 微信Bot新增ScoreSys一键评分命令

## 元信息
- 类型：产出
- 时间：2026-05-15 14:xx
- 优先级：P2 工具改进
- 关联 TODO：微信Bot新增ScoreSys一键评分命令

## 背景
微信 Bot 已有 `/stop`、`/llm`、`/token`、K线图等命令，但缺少与 ScoreSys 选股系统的集成。用户无法通过微信快速获取当日评分 Top10。

## 方案

### 命令设计
用户发送 `/score` → Bot 立即回复"评分已启动" → 后台线程调用 ScoreSys → 完成后推送 Top10

### 实现细节
1. **命令拦截**：在 `on_message()` 的命令区插入 `if text == '/score':` 块，在 `_handle()` 之前返回
2. **异步执行**：`threading.Thread` 后台运行，不阻塞消息循环
3. **调用链**：`subprocess.run([python, main.py, --mock, --output, score_wx_TS.xlsx, --workers, 2], timeout=120)`
4. **结果解析**：`openpyxl` 读取 Excel → 按 score 列降序 → 取 Top10
5. **格式化输出**：奖牌 emoji（🥇🥈🥉）+ 股票名称 + 代码 + 分数
6. **错误处理**：main.py 不存在/超时/Excel 为空/缺少 openpyxl 均有友好提示

### 代码变更
- 文件：`D:\GenericAgent\frontends\wechatapp.py`
- 位置：K线命令 `return` 之后、`def _handle():` 之前
- 新增约 50 行

### Bot 重启
- 旧进程 PID 4568 → 新进程 PID 8484
- 重启后 token 过期，已自动触发重登流程
- 二维码已发给用户 `o9cq80-1u4kvzb2osLB4FHV0X-Zo@im.wechat`

## 验收标准
- [x] `/score` 命令代码已插入 wechatapp.py
- [x] 后台线程异步执行，不阻塞消息循环
- [x] 解析 ScoreSys Excel 输出并格式化 Top10
- [x] Bot 已重启，新代码已加载
- [ ] 用户扫码重登后，发送 `/score` 验证端到端功能

## 待用户操作
1. 用微信扫描二维码完成重登
2. 发送 `/score` 命令验证功能
3. 如 openpyxl 未安装：`pip install openpyxl`

## 记忆更新建议
- L2 微信Bot区块：新增 `/score` 命令功能
- L3 wechat_fix：记录 ScoreSys 集成方案
