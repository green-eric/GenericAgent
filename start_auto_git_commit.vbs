' VBS启动脚本 - auto_git_commit守护进程开机自启
' 使用Shell.Application.ShellExecute实现无窗口后台运行
' 支持开机自启(放入启动文件夹)和手动启动

Option Explicit

Dim objShell, strPython, strScript, strArgs

' 配置路径
strPython = "pythonw.exe"
strScript = "D:\GenericAgent\auto_git_commit.py"

' 使用Shell.Application.ShellExecute无窗口启动
Set objShell = CreateObject("Shell.Application")
objShell.ShellExecute strPython, """" & strScript & """", "", "runas", 0

Set objShell = Nothing