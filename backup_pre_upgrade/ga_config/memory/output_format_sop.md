# 输出格式优化 SOP (2026-05-05)

## 改动范围
1. `assets/sys_prompt.txt` — 新增「输出格式规范」（最高优先级）
2. `frontends/wechatapp.py` — `_clean()` 增强过滤 + `_strip_md()` 增强美化

## sys_prompt 新增规范
- 最终回答：简洁、美观、有结构，emoji + 分隔线/缩进
- 禁止输出过程：不写"调用工具xxx"、"读取文件xxx"等
- 图表优先：表格/进度条(▰▱)/星级(⭐)/排名(🥇🥈🥉或①②③)
- summary ≤30字，只写"做了什么+结果"
- 错误只写"失败原因+下一步"
- 兼容微信富文本和页面渲染

## wechatapp.py _clean 过滤规则
过滤以下行（re.M 模式）：
- `<summary>...</summary>` 整块（re.DOTALL）
- `LLM Running (Turn N) ...`
- `调用工具xxx`、`读取文件 xxx`、`写入文件 xxx`、`执行脚本 xxx`
- `[Driver]...`、`[CDP]...`、`[Timeout...]...`
- `Executing:...`、`Timeout Error...`、`Error:...`、`Traceback...`
- `args: {...}`
- `🛠️ xxx(...)`
- `{"status":...}` 开头的 JSON 结果行
- `=== Response ===`、`=== Prompt ===`
- `"exit_code"`/`"stdout"`/`"stderr"` 开头的行
- `<thinking>...</thinking>`、`<tool_use>...</tool_use>`、`<file_content>...</file_content>`

## wechatapp.py _strip_md 增强映射
- 注意/警告/错误/失败 → ⚠️
- 成功/完成/通过/OK → ✅
- 提示/说明/备注 → 💡
- 推荐/建议/优选 → 👍
- 热门/爆款/大涨 → 🔥
- 上涨/利好/盈利 → 📈
- 下跌/利空/亏损 → 📉

## 备份
- `*.bak_fmt_20260505_102330`
