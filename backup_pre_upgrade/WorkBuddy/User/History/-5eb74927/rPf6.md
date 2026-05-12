# 2026-04-20 工作记忆

## IMA 同步脚本修复

- **问题**：`sync_daily_memory.py` 路径写死为 `Path(__file__).parent`（即 `C:\Users\green\WorkBuddy\Claw`），导致无法找到任何工作区的记忆文件
- **根因**：昨天（4月19日）脚本执行了但直接 `sys.exit(0)` 退出，计划任务返回 0 假成功
- **修复**：改为自动扫描 `C:\Users\green\WorkBuddy\` 下所有子目录的 `.workbuddy/memory/YYYY-MM-DD.md`，合并后同步到 IMA
- **新增功能**：支持命令行参数指定日期（`python sync_daily_memory.py 2026-04-19`），方便补同步历史数据
- **验证**：用 2026-04-18 测试成功，同步了 2 个工作区，笔记 ID: 7451811300509463
