
import subprocess, os

nssm = r"D:\GenericAgent\tools\nssm.exe"
service = "wechatbot"

# Set restart on crash: restart after 5s, 10s, 30s, then reset fail counter after 60s
commands = [
    [nssm, 'set', service, 'AppExit', 'Default', 'Restart'],
    [nssm, 'set', service, 'AppRestartDelay', '5000'],
    [nssm, 'set', service, 'AppStdout', r'D:\GenericAgent\temp\wechatapp_stdout.log'],
    [nssm, 'set', service, 'AppStderr', r'D:\GenericAgent\temp\wechatapp_stderr.log'],
]

for cmd in commands:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    print(f"{' '.join(cmd[-2:])}: rc={r.returncode} {r.stdout.strip()[:100]}")

# Also set via sc.exe for good measure (run as admin)
# failure actions: restart after 5s
r2 = subprocess.run(['sc', 'failure', 'wechatbot', 'reset=', '60', 'actions=', 'restart/5000/restart/10000/restart/30000'], 
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f"sc failure: rc={r2.returncode} {r2.stdout.strip()[:200]}")
