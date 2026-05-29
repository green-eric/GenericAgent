# R146 | 维护 | L3 SOP文件瘦身整理

**时间**: 2026-05-15 | **类型**: 维护

---

## 结论：✅ 完成，23→17个(-26.1%)，超过20%目标

### 删除的文件（4个）

| 文件 | 原因 |
|------|------|
| `scheduled_task_sop.md` | 旧scheduler方案，已被apscheduler替代(R143) |
| `wechat_fix.md` | 一次性修复记录，非SOP |
| `web_setup_sop.md` | 初始安装用，已标注"无需执行此SOP" |
| `token_report.md` | 一次性统计报告，非SOP |

### 合并的文件（3→1）

| 原文件 | → 合并到 |
|--------|---------|
| `mini_sop_env_scan.md` | |
| `mini_sop_memory_update.md` | `mini_sop_collection.md` (97行) |
| `mini_sop_tool_wrapping.md` | |

### 最终17个SOP文件

autonomous_operation_sop, bullish_stream_realtime_sop, cdp_bridge_sop, github_contribution_sop, ljqCtrl_sop+.py, memory_cleanup_sop, memory_management_sop, mini_sop_collection, output_format_sop, plan_sop, procmem_scanner_sop, subagent, supervisor_sop, tmwebdriver_sop, verify_sop, vision_sop, wechat_bot_perf_sop

### 同步更新
- ✅ L3 Insight索引已更新（删除过时条目，添加mini_sop_collection）
- ✅ Git已提交记忆目录变更
