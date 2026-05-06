
import subprocess, time, os, ctypes
from ctypes import wintypes

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def run_cmd(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk', errors='replace', timeout=15)
    return r.stdout.strip(), r.returncode

# 1. 先停止服务
log("Step 1: 停止 wechatbot 服务...")
stdout, rc = run_cmd(['sc', 'stop', 'wechatbot'])
log(f"  sc stop: rc={rc} {stdout}")

# 等待服务完全停止（最多10秒）
for i in range(10):
    time.sleep(1)
    stdout, _ = run_cmd(['sc', 'query', 'wechatbot'])
    if 'STOPPED' in stdout:
        log("  服务已停止")
        break
    log(f"  等待停止... ({i+1}s)")
else:
    log("  ⚠️ 停止超时，强制杀进程...")
    # 强制杀掉所有 pythonw.exe
    kernel32 = ctypes.windll.kernel32
    TH32CS_SNAPPROCESS = 0x00000002
    class PE32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260)]
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    e = PE32(); e.dwSize = ctypes.sizeof(PE32)
    if kernel32.Process32First(snap, ctypes.byref(e)):
        while True:
            exe_name = e.szExeFile.decode('utf-8', errors='replace').lower()
            if exe_name in ('pythonw.exe', 'python.exe'):
                h = kernel32.OpenProcess(0x0001, False, e.th32ProcessID)  # PROCESS_TERMINATE
                if h:
                    log(f"    终止 {exe_name} PID {e.th32ProcessID}")
                    kernel32.TerminateProcess(h, 1)
                    kernel32.CloseHandle(h)
            if not kernel32.Process32Next(snap, ctypes.byref(e)):
                break
    kernel32.CloseHandle(snap)
    time.sleep(2)

# 1.5 清理 .pyc 缓存，确保加载最新代码
log("Step 1.5: 清理 .pyc 缓存...")
import shutil
for _d in [r'D:\GenericAgent\frontends', r'D:\GenericAgent']:
    _pyc = os.path.join(_d, '__pycache__')
    if os.path.exists(_pyc):
        try:
            shutil.rmtree(_pyc)
            log(f"  已清理: {_pyc}")
        except Exception as e:
            log(f"  清理失败: {e}")
    else:
        log(f"  无缓存: {_pyc}")

# 2. 启动服务
log("Step 2: 启动 wechatbot 服务...")
stdout, rc = run_cmd(['sc', 'start', 'wechatbot'])
log(f"  sc start: rc={rc} {stdout}")

# 3. 等待启动
log("等待 8 秒...")
time.sleep(8)

# 4. 检查状态
stdout, _ = run_cmd(['sc', 'query', 'wechatbot'])
log(f"服务状态:\n{stdout}")

if 'RUNNING' in stdout:
    log("✅ wechatbot 服务运行中")
else:
    log("❌ wechatbot 服务未正常运行!")

# 5. 检查日志
log_file = r'D:\GenericAgent\temp\wechatapp.log'
if os.path.exists(log_file):
    with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    log("日志最后5行:")
    for l in lines[-5:]:
        log(f"  {l.strip()}")

log("✅ 重启完成!")
