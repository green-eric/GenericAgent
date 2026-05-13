
Set app = CreateObject("Shell.Application")
app.ShellExecute "pythonw.exe", """D:\GenericAgent\scripts\start_service.py""", "", "runas", 0
