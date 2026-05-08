"""
CDP Bridge 隐身启动脚本
启动Chrome离屏窗口 + CDP bridge，供隐身操作使用
用法: python start_cdp_stealth.py [start|stop|status]
"""
import subprocess, time, os, sys, socket

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def _vbs_path():
    return os.path.join(SCRIPT_DIR, "_start_chrome_stealth.vbs")

def start_stealth():
    """隐身启动Chrome"""
    ps = subprocess.run(['tasklist', '/fi', 'imagename eq chrome.exe', '/fo', 'csv'],
                       capture_output=True, text=True, encoding='gbk')
    if 'chrome' in ps.stdout.lower():
        print("Chrome已在运行，跳过启动")
        return True

    vbs_content = (
        'Set objShell = CreateObject("WScript.Shell")\n'
        'objShell.Run '
        '"' + CHROME.replace('\\', '\\\\') + '"'
        ' --window-position=-32000,-32000'
        ' --window-size=300,300'
        ' https://www.baidu.com'
        ', 7\n'
    )
    with open(_vbs_path(), "w") as f:
        f.write(vbs_content)

    print("正在隐身启动Chrome...")
    subprocess.run(["cscript", "//Nologo", _vbs_path()], capture_output=True, encoding='gbk')
    time.sleep(4)

    ps = subprocess.run(['tasklist', '/fi', 'imagename eq chrome.exe', '/fo', 'csv'],
                       capture_output=True, text=True, encoding='gbk')
    lines = [l for l in ps.stdout.strip().split('\n') if 'chrome' in l.lower()]
    print(f"Chrome进程数: {len(lines)}")
    if len(lines) > 0:
        print("✅ 隐身Chrome启动成功！")
        return True
    else:
        print("❌ Chrome启动失败")
        return False

def stop_stealth():
    """关闭隐身Chrome"""
    print("关闭隐身Chrome...")
    subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'], capture_output=True, encoding='gbk')
    print("已关闭")

def status():
    """查看隐身Chrome状态"""
    ps = subprocess.run(['tasklist', '/fi', 'imagename eq chrome.exe', '/fo', 'csv'],
                       capture_output=True, text=True, encoding='gbk')
    lines = [l for l in ps.stdout.strip().split('\n') if 'chrome' in l.lower()]
    print(f"Chrome进程: {len(lines)} 个")
    for port in [18765, 18766]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        try:
            s.connect(('127.0.0.1', port))
            print(f"端口 {port}: [OK] 监听中")
            s.close()
        except:
            print(f"端口 {port}: [--] 未监听")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"
    if cmd == "start":
        start_stealth()
    elif cmd == "stop":
        stop_stealth()
    elif cmd == "status":
        status()
    else:
        print("用法: python start_cdp_stealth.py [start|stop|status]")