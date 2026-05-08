
import subprocess, time, os

# Stop
r1 = subprocess.run(['nssm', 'stop', 'wechatbot'], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f"stop: rc={r1.returncode} {r1.stdout.strip()[:100]}")
time.sleep(3)

# Start
r2 = subprocess.run(['nssm', 'start', 'wechatbot'], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f"start: rc={r2.returncode} {r2.stdout.strip()[:100]}")
time.sleep(8)

# Check status
r3 = subprocess.run(['sc', 'query', 'wechatbot'], capture_output=True, text=True, encoding='utf-8', errors='replace')
for l in r3.stdout.split('\n'):
    if 'STATE' in l:
        print(f"状态: {l.strip()}")
        break

# Check stderr log
stderr_log = 'D:/GenericAgent/temp/wechatapp_stderr.log'
if os.path.exists(stderr_log):
    with open(stderr_log, encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    print(f"stderr最后5行:")
    for l in lines[-5:]:
        print(f"  {l.rstrip()}")

# Port check
import socket
for port in [18765, 18766]:
    s = socket.socket()
    s.settimeout(2)
    r = s.connect_ex(('127.0.0.1', port))
    s.close()
    print(f"端口{port}: {'占用' if r==0 else '空闲'}")
