
import subprocess, os, sys, time

# Stop service
r = subprocess.run(['sc', 'stop', 'wechatbot'], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f"[admin] sc stop: rc={r.returncode} {r.stdout.strip()[:100]}")
time.sleep(3)

# Kill any remaining python processes in services session
r2 = subprocess.run(['taskkill', '/PID', '3324', '/F'], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f"[admin] taskkill 3324: {r2.stdout.strip()}")
time.sleep(2)

# Now run wechatapp.py directly
print("[admin] Starting wechatapp.py directly...")
r3 = subprocess.run(
    [sys.executable, '-u', r'D:\GenericAgent\frontends\wechatapp.py'],
    capture_output=True, text=True, encoding='utf-8', errors='replace',
    timeout=20,
    cwd=r'D:\GenericAgent'
)
print(f"[admin] wechatapp rc={r3.returncode}")
print(f"[admin] stdout:\n{r3.stdout[-3000:]}")
print(f"[admin] stderr:\n{r3.stderr[-3000:]}")
