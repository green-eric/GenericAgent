# ScoreSys_DailyScore 定时任务诊断

> R170 | 2026-05-18 | 自主行动

---

## 结论：❌ 定时任务从未真正运行过

**根本原因**：登录方式 = "只使用交互方式"，非交互环境下任务触发但不执行。

---

## 证据

### ScoreSys_DailyScore
| 字段 | 值 | 分析 |
|------|-----|------|
| 上次运行时间 | **1999/11/30 0:00:00** | 从未运行（Windows 默认空值） |
| 上次结果 | **267011** | 0x41303 = 任务已触发但未运行 |
| 登录状态 | **只使用交互方式** | 🔴 根因！非交互登录无法执行 |
| 下次运行时间 | 2026/5/18 16:00:00 | 今天 4PM 会再次尝试 |
| 命令 | `python.exe D:\Project\ScoreSys\main.py --from-db --all --save-db` | 命令本身正确 |

### RPS20_DailyBacktest（同样问题）
| 字段 | 值 |
|------|-----|
| 上次运行时间 | **1999/11/30** |
| 上次结果 | **267011** |
| 登录状态 | **只使用交互方式** |

---

## 错误码 267011 含义

`267011` = `0x41303` = `SCHED_S_TASK_HAS_NOT_RUN`（任务已注册但未成功运行）

典型原因：任务配置为"只在用户登录时运行"，但触发时无人登录。

---

## 解决方案

需要用户操作（**必须提供 Windows 密码**）：

### 方法 A：PowerShell 修改（推荐）
```powershell
# 需要管理员权限 + 用户密码
$trigger = New-ScheduledTaskTrigger -Daily -At "16:00"
$principal = New-ScheduledTaskPrincipal -UserId "green" -LogonType Password
Set-ScheduledTask -TaskName "ScoreSys_DailyScore" -Trigger $trigger -Principal $principal
# 运行时会提示输入密码
```

### 方法 B：schtasks 命令行
```cmd
schtasks /change /tn "ScoreSys_DailyScore" /ru green /rp <密码>
```

### 方法 C：手动 GUI
1. 打开 `taskschd.msc`
2. 找到 `ScoreSys_DailyScore`
3. 属性 → 常规 → **安全选项**
4. 改为 **"不管用户是否登录都运行"**
5. 输入密码

---

## 影响

- ⚠️ **scores 表只有 2026-05-15 单日数据**（手动运行产生的）
- ⚠️ **_score_cache 只有单日数据**
- ⚠️ **P0 参数优化被阻塞**（需要多期评分数据）
- ⚠️ **RPS20_DailyBacktest 同样未运行**

---

## 待审

需要用户提供 Windows 密码才能修复定时任务登录方式。

修复后预期：
- ScoreSys_DailyScore 每天 16:00 自动评分
- 积累多期数据后解锁 P0 参数优化
