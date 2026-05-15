import subprocess, time, os, sys, psutil, shutil

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def log_kv(k, v):
    print(f"  {k}: {v}", flush=True)

# ── Step 1: 杀旧进程 ──
log("Step 1: 停止已有 wechatapp...")
killed = 0
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmd = ' '.join(proc.info.get('cmdline') or [])
        if 'wechatapp' in cmd.lower() or 'wxbot' in cmd.lower():
            proc.kill()
            proc.wait(timeout=3)
            log(f"  ✅ 已杀 PID={proc.info['pid']} ({proc.info['name']})")
            killed += 1
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
if killed == 0:
    log("  - 无运行中的 wechatapp")
else:
    log(f"  ✅ 共杀掉 {killed} 个旧进程")

time.sleep(1)

# ── Step 2: 清理 pyc ──
log("Step 2: 清理 .pyc 缓存...")
for _d in [r'D:\GenericAgent\frontends', r'D:\GenericAgent']:
    _pyc = os.path.join(_d, '__pycache__')
    if os.path.exists(_pyc):
        try:
            shutil.rmtree(_pyc)
            log(f"  ✅ 已清理: {_pyc}")
        except Exception as e:
            log(f"  ⚠️ 清理失败: {e}")

# ── Step 3: 启动 bot ──
log("Step 3: 启动 wechatapp...")
python_exe = r'C:\Python312\pythonw.exe'
script = r'D:\GenericAgent\frontends\wechatapp.py'
env = os.environ.copy()
env['HTTP_PROXY'] = 'http://127.0.0.1:7897'
env['HTTPS_PROXY'] = 'http://127.0.0.1:7897'

# 启动日志写到文件，方便排障
_start_log = open(r'D:\GenericAgent\temp\start_service.log', 'a', encoding='utf-8', buffering=1)
_start_log.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 启动 wechatapp...\n")

proc = subprocess.Popen(
    [python_exe, script],
    cwd=r'D:\GenericAgent',
    env=env,
    stdout=_start_log,
    stderr=_start_log,
)
log(f"  ✅ 已启动 (PID={proc.pid})")

# ── Step 4: 等待并检查 ──
log("Step 4: 检查启动状态...")
time.sleep(5)
running = False
for proc2 in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmd = ' '.join(proc2.info.get('cmdline') or []).lower()
        if 'wechatapp' in cmd:
            log(f"  ✅ wechatapp 运行中 (PID={proc2.info['pid']})")
            running = True
    except:
        pass
if not running:
    log("  ❌ wechatapp 进程未找到!")

log_file = r'D:\GenericAgent\temp\wechatapp.log'
if os.path.exists(log_file):
    with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    log("  日志最后5行:")
    for l in lines[-5:]:
        log(f"    {l.strip()}")
else:
    log("  - 日志文件不存在")

log("✅ 启动完成!")