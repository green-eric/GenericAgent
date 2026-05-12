import subprocess, sys, os
os.chdir(r"C:\Users\green\WorkBuddy\20260424203734\workplace")
cmd = [
    r"C:\Users\green\AppData\Local\Python\bin\python.exe",
    "stock_analyzer.py",
    "--workers", "16",
    "--timeout", "7200",
]
log = open("run_v5_rerun.log", "w", encoding="utf-8")
err = open("run_v5_rerun_err.log", "w", encoding="utf-8")
p = subprocess.Popen(cmd, stdout=log, stderr=err)
print(f"Started PID {p.pid}")
log.close()
err.close()
