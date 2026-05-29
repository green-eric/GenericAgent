# R224 | file_monitor_v3守护进程化

## 目标
将 file_monitor_v3 改造为开机自启 + 崩溃自动重启的守护进程

## 方案
由于 schtasks 需要管理员权限（拒绝访问），改用启动文件夹方式:
- 路径: C:\Users\green\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\
- 无需管理员权限，当前用户登录时自动启动

## 产出
1. 包装脚本: file_monitor_v3_wrapper.bat (186 bytes)
   - 无限循环 + 5秒延迟重启
   - 退出后自动拉起
2. 启动项: Startup/GA_FileMonitor_v3.bat (已复制)

## 测试结果
- 包装脚本启动: 成功
- 子进程 python.exe: 运行中
- conhost.exe: 正常
- 启动文件夹文件: 存在

## 注意事项
- schtasks 方式因权限不足失败，启动文件夹是最佳替代
- 如需开机自启（无需登录），需要管理员权限配置计划任务
- 崩溃重启间隔: 5秒
