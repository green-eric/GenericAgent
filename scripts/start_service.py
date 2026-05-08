
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
    log("  ⚠️ 停止超时，精准杀 wechatbot 进程...")
    nssm_exe = r"D:\GenericAgent\tools\nssm.exe"
    # 通过 nssm 获取 wechatbot 的实际 PID
    out, _ = run_cmd([nssm_exe, 'status', 'wechatbot'])
    # nssm status 不直接给 PID，用 sc queryex 获取
    out, _ = run_cmd(['sc', 'queryex', 'wechatbot'])
    pid = None
    for line in out.split('\n'):
        if 'PID' in line:
            try:
                pid = int(line.split(':')[1].strip())
            except:
                pass
    if pid:
        log(f"  wechatbot PID={pid}，精准终止...")
        kernel32 = ctypes.windll.kernel32
        h = kernel32.OpenProcess(0x0001, False, pid)
        if h:
            kernel32.TerminateProcess(h, 1)
            kernel32.CloseHandle(h)
            log(f"  ✅ 已终止 PID {pid}")
        else:
            log(f"  ⚠️ 无法打开 PID {pid}")
    else:
        log("  ⚠️ 未找到 wechatbot PID，可能已停止")
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
