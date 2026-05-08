
Set app = CreateObject("Shell.Application")
app.ShellExecute "python.exe", """D:\GenericAgent\scripts\start_service.py""", "", "runas", 1
