"""
GA Watchdog - monitor launch.pyw + wechatbot service
Auto-restart on crash, check every 60s
No admin required

v2 fixes:
  (1) 修复 PowerShell fallback 查询语法错误（无效查询 → 假阴性）
  (2) ctypes 模块级导入，避免函数内重复 import 失败
  (3) 冷却期：重启后 120s 内不检查对应组件
  (4) 频率限制：10 分钟内同组件最多重启 3 次
"""
import subprocess, time, os, sys, ctypes
from ctypes import wintypes

LOG = r"D:\GenericAgent\temp\watchdog.log"
GA_DIR = r"D:\GenericAgent"
LAUNCH_SCRIPT = r"D:\GenericAgent\launch.pyw"
WECHATAPP = r"D:\GenericAgent\frontends\wechatapp.py"
PYTHONW = r"C:\Users\green\AppData\Local\Programs\Python\Python312\pythonw.exe"

# 所有 subprocess 调用强制不弹 CMD 窗口
NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW

# ============ 全局状态 ============
_MUTEX_NAME = r"Global\GenericAgent_Launch_Mutex"
# 冷却期 & 频率限制
_GA_COOLDOWN_UNTIL = 0
_WX_COOLDOWN_UNTIL = 0
_GA_RESTART_TIMES = []   # list of epoch timestamps
_WX_RESTART_TIMES = []
MAX_RESTARTS = 3
RESTART_WINDOW = 600     # 10 minutes
COOLDOWN_SEC = 120       # 2 minutes after restart

# 预绑定 Win32 API
_CreateMutex = ctypes.windll.kernel32.CreateMutexW
_CreateMutex.argtypes = [wintypes.LPCVOID, wintypes.BOOL, wintypes.LPCWSTR]
_CreateMutex.restype = wintypes.HANDLE
_CloseHandle = ctypes.windll.kernel32.CloseHandle
_GetLastError = ctypes.windll.kernel32.GetLastError


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
    """检测 GA 是否存活。mutex 主方法 + 修复版 PowerShell fallback"""
    # 方法1: Mutex (快速可靠)
    for attempt in range(3):
        try:
            _h = _CreateMutex(None, True, _MUTEX_NAME)
            _err = _GetLastError()
            if _h:
                _CloseHandle(_h)
            if _err == 183:
                return True
            # mutex 不存在，等 1s 重试（应对启动时序）
            if attempt < 2:
                time.sleep(1)
        except Exception as e:
            log(f"    Mutex check attempt {attempt+1} error: {e}")
            if attempt < 2:
                time.sleep(1)

    # 方法2: PowerShell 进程扫描 (fallback) — 修复引号转义
    # 使用单引号包裹 PowerShell 命令避免 \" 转义失败
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" "
        "| Where-Object { $_.CommandLine -match 'launch[.]pyw' } "
        "| Select-Object -ExpandProperty ProcessId"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=15, creationflags=NO_WINDOW
        )
        if r.stdout.strip():
            return True
        # stderr being non-empty doesn't necessarily mean failure
        return False
    except subprocess.TimeoutExpired:
        log("    ⚠️ PowerShell GA check timed out (15s)")
        return False
    except Exception as e:
        log(f"    ⚠️ PowerShell GA check error: {e}")
        return False


def is_wechatbot_alive():
    """检测 wechatbot 是否存活。修复版 PowerShell"""
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" "
        "| Where-Object { $_.CommandLine -match 'wechatapp' } "
        "| Select-Object -ExpandProperty ProcessId"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=15, creationflags=NO_WINDOW
        )
        return bool(r.stdout.strip())
    except Exception as e:
        log(f"    ⚠️ PowerShell WX check error: {e}")
        return False


def _rate_limited(restart_times):
    """检查是否超过频率限制。返回 True 表示被限流"""
    now = time.time()
    # 清理旧记录
    restart_times[:] = [t for t in restart_times if now - t < RESTART_WINDOW]
    return len(restart_times) >= MAX_RESTARTS


def restart_ga():
    global _GA_COOLDOWN_UNTIL
    if _rate_limited(_GA_RESTART_TIMES):
        log("  🚫 GA restart rate-limited (max 3/10min). Skipping.")
        return
    _GA_RESTART_TIMES.append(time.time())

    log("  Killing old launch.pyw instances...")
    ps_kill = (
        "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" "
        "| Where-Object { $_.CommandLine -match 'launch[.]pyw' } "
        "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_kill],
        capture_output=True, timeout=15, creationflags=NO_WINDOW
    )
    time.sleep(3)

    # 验证杀干净
    if is_ga_alive():
        log("  ⚠️ Old GA still alive after kill, retry...")
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_kill],
            capture_output=True, timeout=15, creationflags=NO_WINDOW
        )
        time.sleep(3)

    if is_ga_alive():
        log("  ❌ Cannot kill old GA. Skipping restart.")
        return

    log("  Starting GA (launch.pyw)...")
    subprocess.Popen(
        [PYTHONW, LAUNCH_SCRIPT],
        cwd=GA_DIR, creationflags=NO_WINDOW
    )
    log(f"  ✅ GA started. Cooldown {COOLDOWN_SEC}s")
    _GA_COOLDOWN_UNTIL = time.time() + COOLDOWN_SEC


def restart_wechatbot():
    global _WX_COOLDOWN_UNTIL
    if _rate_limited(_WX_RESTART_TIMES):
        log("  🚫 WX restart rate-limited (max 3/10min). Skipping.")
        return
    _WX_RESTART_TIMES.append(time.time())

    log("  Killing old wechatapp instances...")
    ps_kill = (
        "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" "
        "| Where-Object { $_.CommandLine -match 'wechatapp' } "
        "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_kill],
        capture_output=True, timeout=15, creationflags=NO_WINDOW
    )
    time.sleep(3)

    if is_wechatbot_alive():
        log("  ⚠️ Old wechatbot still alive, retry...")
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_kill],
            capture_output=True, timeout=15, creationflags=NO_WINDOW
        )
        time.sleep(3)

    if is_wechatbot_alive():
        log("  ❌ Cannot kill old wechatbot. Skipping restart.")
        return

    log("  Starting wechatbot (wechatapp.py)...")
    subprocess.Popen(
        [PYTHONW, WECHATAPP],
        cwd=GA_DIR, creationflags=NO_WINDOW
    )
    log(f"  ✅ wechatbot started. Cooldown {COOLDOWN_SEC}s")
    _WX_COOLDOWN_UNTIL = time.time() + COOLDOWN_SEC


def main():
    global _GA_COOLDOWN_UNTIL, _WX_COOLDOWN_UNTIL
    log("=" * 50)
    log("GA Watchdog started (v2: cooldown + rate-limit)")
    log("=" * 50)

    try:
        if sys.platform == "win32":
            ctypes.windll.user32.ShowWindow(
                ctypes.windll.kernel32.GetConsoleWindow(), 0
            )
    except:
        pass

    fail_ga = 0
    fail_wx = 0

    while True:
        try:
            now = time.time()

            # --- GA ---
            if now < _GA_COOLDOWN_UNTIL:
                # 冷却期内，跳过检测，不改变 fail_ga
                pass
            elif is_ga_alive():
                if fail_ga > 0:
                    log("  GA recovered ✓")
                fail_ga = 0
            else:
                fail_ga += 1
                log(f"  GA not running! (consecutive={fail_ga})")
                if fail_ga >= 2:
                    log("  Restarting GA...")
                    restart_ga()
                    fail_ga = 0
                    # 冷却期已在 restart_ga 内设置

            # --- WeChatBot ---
            if now < _WX_COOLDOWN_UNTIL:
                pass
            elif is_wechatbot_alive():
                if fail_wx > 0:
                    log("  wechatbot recovered ✓")
                fail_wx = 0
            else:
                fail_wx += 1
                log(f"  wechatbot not running! (consecutive={fail_wx})")
                if fail_wx >= 3:
                    log("  Restarting wechatbot...")
                    restart_wechatbot()
                    fail_wx = 0

        except Exception as e:
            log(f"  ⚠️ Check error: {e}")

        time.sleep(60)


if __name__ == "__main__":
    main()