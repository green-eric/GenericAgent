# R231 | 能力 | Windows服务化GA核心守护

## 结论
⚠️ **部分完成** — ga_service_manager.py 创建完成，但 nssm 安装 Windows 服务需要管理员权限，无法在自动化模式下执行。

## 已完成
1. ✅ nssm 2.24 下载并解压到 ./nssm/nssm-2.24/win32/nssm.exe
2. ✅ ga_service_manager.py 创建完成 (4692 bytes)
   - 支持 install/start/stop/restart/status/uninstall 命令
   - 3个服务配置：ga_file_monitor / ga_scheduler / ga_auto_git
   - 崩溃自动重启（5秒延迟）
   - stdout/stderr 日志分离
3. ✅ 手动安装指南生成

## 服务配置

| 服务名 | 脚本 | 启动类型 | 说明 |
|--------|------|---------|------|
| ga_file_monitor | file_monitor_v3.py | auto | 文件监控触发回测 |
| ga_scheduler | scheduler.py | auto | 定时任务调度器 |
| ga_auto_git | auto_git_commit.py | auto | 自动Git提交 |

## 手动安装步骤（需管理员权限）

以管理员身份运行 CMD 或 PowerShell:

```batch
cd D:\GenericAgent\temp

:: 安装三个服务
python ga_service_manager.py install

:: 启动服务
python ga_service_manager.py start

:: 查看状态
python ga_service_manager.py status
```

## 阻塞项
- ❌ nssm 安装服务需要管理员权限
- ❌ 无法在自动化模式下完成安装
- ✅ 所有脚本和配置已就绪，用户在场时一键安装

## 建议
下次用户在场时，以管理员身份运行 `python ga_service_manager.py install && python ga_service_manager.py start` 即可完成全部安装。
