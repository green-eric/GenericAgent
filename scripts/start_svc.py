
import subprocess, time

r = subprocess.run(['sc', 'start', 'wechatbot'], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f"sc start: rc={r.returncode} {r.stdout.strip()}")
time.sleep(8)

r2 = subprocess.run(['sc', 'query', 'wechatbot'], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f"\n服务状态:\n{r2.stdout}")
