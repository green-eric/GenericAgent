# 长期工作记忆

## IMA 知识库同步配置

### 凭证存储
- **Client ID**: 存储在 `~/.config/ima/client_id`
- **API Key**: 存储在 `~/.config/ima/api_key`
- **安全提示**: 凭证仅本地存储，未上传云端

### 同步脚本
- **脚本路径**: `sync_daily_memory.py` (工作区根目录)
- **功能**: 自动读取当日工作记忆文件 (`YYYY-MM-DD.md`)，创建IMA笔记
- **执行频率**: 每日18:00通过Windows计划任务自动运行
- **笔记标题格式**: `WorkBuddy 工作记忆 - YYYY-MM-DD`

### 计划任务
- **任务名称**: `WorkBuddy-IMA-Sync`
- **触发器**: 每日18:00
- **操作**: 运行 `python sync_daily_memory.py`
- **工作目录**: 工作区根目录
- **状态**: 已启用 (Ready)

### 管理命令
```powershell
# 查看任务
Get-ScheduledTask -TaskName "WorkBuddy-IMA-Sync"

# 手动运行任务
Start-ScheduledTask -TaskName "WorkBuddy-IMA-Sync"

# 删除任务
Unregister-ScheduledTask -TaskName "WorkBuddy-IMA-Sync" -Confirm:$false

# 修改触发时间
# 需要重新创建任务，或通过任务计划程序GUI修改
```

### 故障排查
1. **同步失败检查**:
   - 确认凭证文件存在且内容正确
   - 检查网络连接
   - 查看Python脚本输出日志（可通过手动运行调试）

2. **计划任务不运行**:
   - 检查任务状态: `Get-ScheduledTask -TaskName "WorkBuddy-IMA-Sync"`
   - 查看最近运行结果: 通过任务计划程序GUI查看历史记录
   - 确保Python在系统PATH中

3. **IMA笔记未创建**:
   - 手动运行脚本测试: `python sync_daily_memory.py`
   - 检查IMA API响应（可能需要更新凭证）

### 微信小程序访问
- 使用相同账户登录IMA微信小程序
- 在"我的笔记"中查看同步的工作记忆
- 笔记按日期标题组织，便于查找