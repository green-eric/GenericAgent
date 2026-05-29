# R287 — ScoreSys 信号自动推送配置

> 时间: 2026-05-26 | 类型: 配置 | 自主行动

---

## 1. 目标

为已部署的 `daily_health_check.py` 配置 Windows 计划任务，实现每日 18:00 自动运行 + 异常时微信推送告警。

## 2. 执行步骤

### 2.1 日检脚本验证

手动运行 `python daily_health_check.py --quiet`，确认脚本正常：
- ✅ 数据库连接正常
- ✅ quotes: 3,244,131 行 | financials: 192,904 行 | stocks: 4,344 | scores: 39,064
- ✅ 最新行情: 2026-05-25 | 最新评分: 2026-05-25 | 覆盖 4344 只
- ✅ 信号文件: 404 只, 12.0h 前更新
- ✅ 评分分布: 平均 51.65, 范围 0.0~74.0, ≥60: 1036 只, ≥65: 318 只
- ✅ EXIT CODE: 0

### 2.2 计划任务注册

使用 `schtasks /create /xml` 注册任务：

| 项目 | 值 |
|------|-----|
| 任务名 | `ScoreSys_DailyHealthCheck` |
| 执行时间 | 每日 18:00 |
| 执行命令 | `python daily_health_check.py --push` |
| 工作目录 | `D:\Project\ScoreSys` |
| 超时 | 30 分钟 |
| 电源限制 | 不限制（插电/电池均执行） |

### 2.3 手动触发测试

`schtasks /run` 手动触发，任务状态显示 **"正在运行"**，EXIT CODE: 0。

## 3. 配置详情

### XML 任务定义
- 路径: `D:\GenericAgent\temp\scoresys_daily_task.xml`
- 格式: Task v1.2 (Windows Vista+)
- 触发器: CalendarTrigger, 每日 18:00 从 2026-05-27 开始
- 操作: Exec, 运行 `python daily_health_check.py --push`

### 微信推送机制
- 脚本 `--push` 参数触发推送
- 推送内容: 日检报告摘要 + 异常告警
- 推送目标: 微信 Bot

## 4. 验证清单

- [x] 日检脚本手动运行正常 (EXIT 0)
- [x] 计划任务注册成功 (schtasks EXIT 0)
- [x] 手动触发测试通过 (状态: 正在运行)
- [ ] 连续 7 天自动运行验证（需时间积累）
- [ ] 异常告警推送验证（需模拟异常场景）

## 5. 后续建议

- 7 天后检查任务运行历史: `schtasks /query /tn ScoreSys_DailyHealthCheck /v /fo LIST`
- 如需调整时间: `schtasks /change /tn ScoreSys_DailyHealthCheck /st 17:30`
- 如需删除任务: `schtasks /delete /tn ScoreSys_DailyHealthCheck /f`

---

*配置完成于自主行动 R287*
