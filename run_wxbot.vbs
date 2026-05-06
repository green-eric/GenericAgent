Set app = CreateObject("Shell.Application")
app.ShellExecute "python.exe", """D:\GenericAgent\temp\start_service.py""", "", "runas", 1
