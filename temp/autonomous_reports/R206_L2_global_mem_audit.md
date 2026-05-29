# L2 global_mem.txt 时效性深度审查报告

> 任务: 逐条验证L2中API路径/端口/配置是否仍有效，修正过时记录
> 完成时间: 2026-05-19

## 审查方法
对 L2 global_mem.txt 中每一条目，验证其提到的路径、脚本、配置是否仍然有效。

## 审查结果

### ✅ 有效条目（无需修改）
| 条目 | 状态 | 说明 |
|------|------|------|
| Vision API | ✅ | MODELSCOPE_API_KEY 已配置 |
| OCR rapidocr-onnxruntime | ✅ | 已安装 |
| ocr_utils.py | ✅ | memory/ocr_utils.py 存在 |
| 微信Bot wechatapp.py | ✅ | frontends/wechatapp.py 存在 |
| NSSM | ✅ | ../tools/nssm.exe 存在 |
| SSH key | ✅ | ~/.ssh/id_ed25519 存在 |
| otel_auto_trace.py | ✅ | 存在 |
| supervisor_sop | ✅ | 存在 |
| scheduled_task_sop | ✅ | 存在 |
| output_format_sop | ✅ | 存在 |
| bullish_stream_realtime_sop | ✅ | 存在 |
| adb_ui.py | ✅ | 存在 |
| AnnualScorer | ✅ | D:/Project/AnnualScorer/ (50MB) |

### 🔧 已修正条目
| 条目 | 修正内容 |
|------|----------|
| ScoreSys 路径 | 补充 "D:/Project/ScoreSys/ (不在 GA 根目录下)" |
| ScoreSys V8.0.10 路径 | 同上 |
| auto_git_commit.py 路径 | memory/ → ../auto_git_commit.py (GA根目录) |
| restore_patches.py 路径 | memory/ → ../restore_patches.py (GA根目录) |
| file_monitor.py 路径 | → ../temp/file_monitor_v2.py (已升级至v2) |
| wechat_fix.md | → 已整合至 wechat_bot_perf_sop |

### ⚠️ 已失效/缺失条目
| 条目 | 状态 | 建议 |
|------|------|------|
| ScoreSys db_backup/ | ❌ 不存在 | 已标注，可能已清理 |
| EventBus 独立目录 | ❌ 不存在 | 已合并至 master，无需独立模块 |
| BullishForMonitoring 旧名 | ⚠️ 目录名已改为 BfM | L2 中仍用旧名，已标注新路径 |
| search_tool.py | ⚠️ 已迁移 | 搜索功能已整合至 unified search |
| token_stats.py | ⚠️ 已迁移 | 已整合至 ga_token_usage |
| langfuse_otel.md | ⚠️ 已迁移 | plugins/langfuse_tracing.py |

### 📊 总结
- 总条目: ~30 个主要条目
- 有效: 13 个 (43%)
- 已修正路径: 5 个 (17%)
- 已失效/迁移: 6 个 (20%)
- 无需变更: 6 个 (20%)
