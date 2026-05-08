
import subprocess

# Set AppDirectory to D:\GenericAgent
r1 = subprocess.run(['nssm', 'set', 'wechatbot', 'AppDirectory', 'D:\\GenericAgent'], 
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f"set AppDirectory: {r1.stdout.strip()} rc={r1.returncode}")

# Also set AppEnvironment to ensure PYTHONPATH is correct
r2 = subprocess.run(['nssm', 'set', 'wechatbot', 'AppEnvironment', 'PYTHONPATH=D:\\GenericAgent'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f"set AppEnvironment: {r2.stdout.strip()} rc={r2.returncode}")

# Verify
r3 = subprocess.run(['nssm', 'get', 'wechatbot', 'AppDirectory'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f"verify AppDirectory: {r3.stdout.strip()}")
