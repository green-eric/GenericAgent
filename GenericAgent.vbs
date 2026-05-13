Set WshShell = CreateObject("WScript.Shell")
pythonwPath = "C:\Python314\pythonw.exe"
scriptPath = "D:\GenericAgent\launch.pyw"
WshShell.Run """" & pythonwPath & """ """ & scriptPath & """", 0, False
