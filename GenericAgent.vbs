Set WshShell = CreateObject("WScript.Shell")
pythonwPath = "C:\Users\green\AppData\Local\Programs\Python\Python312\pythonw.exe"
scriptPath = "D:\GenericAgent\launch.pyw"
WshShell.Run """" & pythonwPath & """ """ & scriptPath & """", 0, False
