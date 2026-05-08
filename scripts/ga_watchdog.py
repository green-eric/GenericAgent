"""
GA Watchdog - monitor launch.pyw + wechatbot service
Auto-restart on crash, check every 60s
No admin required
"""
import subprocess, time, os, sys, ctypes

LOG = r"D:\GenericAgent\temp\watchdog.log"
GA_DIR = r"D:\GenericAgent"
LAUNCH_SCRIPT = r"D:\GenericAgent\launch.pyw"
PYTHONW = r"C:\Users\green\AppData\Local\Programs\Python\Python312\pythonw.exe"
NSSM = r"D:\GenericAgent\tools\nssm.exe"

# 关键修复：所有 subprocess 调用强制不弹 CMD 窗口
NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass

def is_ga_alive():
    ps = r"Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object { $_.CommandLine -match 'launch\.pyw' } | Select-Object ProcessId"
    r = subprocess.run(["powershell", "-Command", ps], capture_output=True, text=True, timeout=10, creationflags=NO_WINDOW)
    return "ProcessId" in r.stdout

def is_wechatbot_alive():
    r = subprocess.run(["sc", "query", "wechatbot"], capture_output=True, text=True, encoding="gbk", errors="replace", timeout=10, creationflags=NO_WINDOW)
    return "RUNNING" in r.stdout

def restart_ga():
    log("  Killing old launch.pyw instances...")
    ps_kill = r"Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object { $_.CommandLine -match 'launch\.pyw' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('Killed PID '+$_.ProcessId) }"
    subprocess.run(["powershell", "-Command", ps_kill], capture_output=True, timeout=10, creationflags=NO_WINDOW)
    time.sleep(2)
    log("  Starting GA (launch.pyw)...")
    subprocess.Popen([PYTHONW, LAUNCH_SCRIPT], cwd=GA_DIR, creationflags=0x08000000)

def restart_wechatbot():
    log("  Restarting wechatbot service...")
    subprocess.run([NSSM, "stop", "wechatbot"], capture_output=True, timeout=10, creationflags=NO_WINDOW)
    time.sleep(3)
    subprocess.run([NSSM, "start", "wechatbot"], capture_output=True, timeout=10, creationflags=NO_WINDOW)

def main():
    log("=" * 50)
    log("GA Watchdog started")
    log("Monitoring: launch.pyw + wechatbot service")
    log("=" * 50)
    try:
        if sys.platform == "win32":
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass
    fail_ga = 0
    fail_wx = 0
    while True:
        try:
            if is_ga_alive():
                if fail_ga > 0:
                    log("  GA recovered")
                fail_ga = 0
            else:
                fail_ga += 1
                log(f"  GA not running! (consecutive={fail_ga})")
                if fail_ga >= 2:
                    log("  Restarting GA...")
                    restart_ga()
                    fail_ga = 0
            if is_wechatbot_alive():
                if fail_wx > 0:
                    log("  wechatbot recovered")
                fail_wx = 0
            else:
                fail_wx += 1
                log(f"  wechatbot not running! (consecutive={fail_wx})")
                if fail_wx >= 3:
                    log("  Restarting wechatbot...")
                    restart_wechatbot()
                    fail_wx = 0
        except Exception as e:
            log(f"  Check error: {e}")
        time.sleep(60)

if __name__ == "__main__":
    main()
