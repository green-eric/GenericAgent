
import subprocess, sys, os
nssm = r"D:\GenericAgent\tools\nssm.exe"
python_exe = sys.executable
wechat_script = r"D:\GenericAgent\frontends\wechatapp.py"
work_dir = r"D:\GenericAgent\frontends"

# Install
subprocess.run([nssm, 'install', 'wechatbot', python_exe, wechat_script], check=True)
subprocess.run([nssm, 'set', 'wechatbot', 'AppDirectory', work_dir], check=True)
subprocess.run([nssm, 'set', 'wechatbot', 'AppStdout', r"D:\GenericAgent\temp\wechatapp.log"], check=True)
subprocess.run([nssm, 'set', 'wechatbot', 'AppStderr', r"D:\GenericAgent\temp\wechatapp.log"], check=True)
subprocess.run([nssm, 'set', 'wechatbot', 'AppRestartDelay', '5000'], check=True)
subprocess.run([nssm, 'set', 'wechatbot', 'Start', 'SERVICE_AUTO_START'], check=True)
print("Service installed!")
