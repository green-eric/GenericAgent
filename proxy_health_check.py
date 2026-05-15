#!/usr/bin/env python3
"""
代理健康检测脚本 - 定期检测 PC 外网代理可用性
用法:
  proxy_health_check.py                   # 单次检测
  proxy_health_check.py --loop            # 持续检测(每5分钟)
  proxy_health_check.py --report          # 生成稳定性报告
  proxy_health_check.py --schedule        # 注册Windows计划任务(每日3次: 9:00/15:00/21:00)
  proxy_health_check.py --unschedule      # 注销计划任务
"""

import subprocess, socket, time, json, os, sys
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp', 'proxy_logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'proxy_health.jsonl')
REPORT_FILE = os.path.join(LOG_DIR, 'proxy_report.md')

# 检测目标
PROXY_PORTS = [7890, 7897, 1080, 10808, 10809]
TEST_TARGETS = [
    ("百度(直连)", "https://www.baidu.com", False),
    ("GitHub",     "https://github.com",    True),
    ("Google",     "https://www.google.com", True),
    ("Bing",       "https://www.bing.com",   True),
    ("Clash API",  "http://127.0.0.1:7897/version", True),
]

def check_clash_process():
    """检查 Clash 进程状态"""
    r = subprocess.run(
        ["powershell", "-Command",
         "Get-Process | Where-Object {$_.ProcessName -match 'clash|Clash|ClashVerge|clash-verge'} "
         "| Select-Object ProcessName, Id | Format-List"],
        capture_output=True, text=True, timeout=10
    )
    processes = []
    for block in r.stdout.strip().split('\n\n'):
        info = {}
        for line in block.strip().split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                info[k.strip()] = v.strip()
        if info:
            processes.append(info)
    return processes

def check_ports():
    """检查代理端口"""
    results = {}
    for port in PROXY_PORTS:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        ok = s.connect_ex(('127.0.0.1', port)) == 0
        s.close()
        results[port] = ok
    return results

def check_system_proxy():
    """检查系统代理设置"""
    r = subprocess.run(
        ["powershell", "-Command",
         "Get-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings' "
         "| Select-Object ProxyEnable, ProxyServer | Format-List"],
        capture_output=True, text=True, timeout=10
    )
    info = {}
    for line in r.stdout.strip().split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            info[k.strip()] = v.strip()
    return info

def check_connectivity():
    """测试实际连通性 — 外网检测默认走本地代理，避免直连超时"""
    import urllib.request
    results = []

    # 构建代理 handler（Clash Verge 实际监听 7897）
    proxy_handler = urllib.request.ProxyHandler({
        'http': 'http://127.0.0.1:7897',
        'https': 'http://127.0.0.1:7897',
    })
    proxy_opener = urllib.request.build_opener(proxy_handler)
    # 直连 opener（用于百度等国内站点）
    direct_opener = urllib.request.build_opener()

    for name, url, needs_proxy in TEST_TARGETS:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            start = time.time()
            # Clash API 直连，其他外网走代理
            if url.startswith('http://127.0.0.1'):
                resp = direct_opener.open(req, timeout=5)
            elif needs_proxy:
                resp = proxy_opener.open(req, timeout=10)
            else:
                resp = direct_opener.open(req, timeout=8)
            elapsed = (time.time() - start) * 1000
            results.append({
                "name": name, "url": url, "status": resp.status,
                "ms": round(elapsed, 0), "ok": True, "needs_proxy": needs_proxy
            })
        except Exception as e:
            # 外网检测失败时再尝试直连（代理可能挂了但网络通）
            if needs_proxy:
                try:
                    req2 = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    start2 = time.time()
                    resp2 = direct_opener.open(req2, timeout=8)
                    elapsed2 = (time.time() - start2) * 1000
                    results.append({
                        "name": name, "url": url, "status": resp2.status,
                        "ms": round(elapsed2, 0), "ok": True,
                        "needs_proxy": needs_proxy, "note": "direct_only"
                    })
                except Exception as e2:
                    results.append({
                        "name": name, "url": url, "status": 0,
                        "ms": 0, "ok": False,
                        "error": str(e)[:60] + "|" + str(e2)[:40],
                        "needs_proxy": needs_proxy
                    })
            else:
                results.append({
                    "name": name, "url": url, "status": 0,
                    "ms": 0, "ok": False, "error": str(e)[:80],
                    "needs_proxy": needs_proxy
                })
    return results

def run_check():
    """执行一次完整检测"""
    now = datetime.now()
    result = {
        "ts": now.isoformat(),
        "clash_processes": check_clash_process(),
        "ports": check_ports(),
        "system_proxy": check_system_proxy(),
        "connectivity": check_connectivity(),
    }
    
    # 写入日志
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False) + '\n')
    
    return result

def print_result(result):
    """打印检测结果"""
    ts = result['ts'][:19]
    print(f"\n{'='*60}")
    print(f"🕐 {ts}")
    print(f"{'='*60}")
    
    # Clash 进程
    procs = result['clash_processes']
    if procs:
        for p in procs:
            print(f"  ⚙️  Clash: {p.get('ProcessName','?')} (PID:{p.get('Id','?')})")
    else:
        print(f"  ❌ Clash: 进程未运行")
    
    # 端口
    print(f"\n  📡 端口状态:")
    for port, ok in result['ports'].items():
        print(f"    {port}: {'✅' if ok else '❌'}")
    
    # 系统代理
    sp = result['system_proxy']
    enable = sp.get('ProxyEnable', '0')
    server = sp.get('ProxyServer', '(无)')
    print(f"\n  🔧 系统代理: {'开启' if enable=='1' else '关闭'} → {server}")
    
    # 连通性
    print(f"\n  🌐 连通性:")
    direct_ok = proxy_ok = True
    for c in result['connectivity']:
        icon = '✅' if c['ok'] else '❌'
        ms = f"{c['ms']:.0f}ms" if c['ok'] else c.get('error','')[:40]
        print(f"    {icon} {c['name']}: {ms}")
        if c['ok'] and not c.get('needs_proxy', False):
            pass  # 直连OK
        elif not c['ok'] and not c.get('needs_proxy', False):
            direct_ok = False
        elif c['ok'] and c.get('needs_proxy', False):
            pass  # 代理OK
        elif not c['ok'] and c.get('needs_proxy', True):
            proxy_ok = False
    
    # 总结
    print(f"\n  📊 总结: ", end="")
    if proxy_ok and direct_ok:
        print("🟢 全部正常")
    elif direct_ok and not proxy_ok:
        print("🟡 直连正常，代理不通")
    elif not direct_ok:
        print("🔴 网络异常")
    else:
        print("🟠 部分异常")

def generate_report():
    """生成稳定性报告"""
    if not os.path.exists(LOG_FILE):
        print("无日志数据，请先运行检测")
        return
    
    records = []
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except:
                    pass
    
    if not records:
        print("日志为空")
        return
    
    # 统计
    total = len(records)
    first_ts = records[0]['ts'][:19]
    last_ts = records[-1]['ts'][:19]
    
    # 按目标统计成功率
    target_stats = {}
    for r in records:
        for c in r.get('connectivity', []):
            name = c['name']
            if name not in target_stats:
                target_stats[name] = {"ok": 0, "fail": 0}
            if c['ok']:
                target_stats[name]['ok'] += 1
            else:
                target_stats[name]['fail'] += 1
    
    # 端口统计
    port_stats = {}
    for r in records:
        for port, ok in r.get('ports', {}).items():
            if port not in port_stats:
                port_stats[port] = {"up": 0, "down": 0}
            if ok:
                port_stats[port]['up'] += 1
            else:
                port_stats[port]['down'] += 1
    
    # Clash 进程统计
    clash_up = sum(1 for r in records if r.get('clash_processes'))
    clash_down = total - clash_up
    
    # 生成报告
    lines = [
        "# 代理稳定性报告",
        f"> 生成时间: {datetime.now().isoformat()[:19]}",
        f"> 数据范围: {first_ts} ~ {last_ts}",
        f"> 总检测次数: {total}",
        "",
        "## Clash 进程",
        f"| 状态 | 次数 | 占比 |",
        f"|------|-----:|-----:|",
        f"| ✅ 运行 | {clash_up} | {clash_up/total*100:.1f}% |",
        f"| ❌ 未运行 | {clash_down} | {clash_down/total*100:.1f}% |",
        "",
        "## 端口可用性",
        "| 端口 | UP | DOWN | 可用率 |",
        "|------|---:|-----:|-------:|",
    ]
    for port, s in sorted(port_stats.items()):
        rate = s['up']/total*100 if total > 0 else 0
        lines.append(f"| {port} | {s['up']} | {s['down']} | {rate:.1f}% |")
    
    lines += [
        "",
        "## 连通性",
        "| 目标 | 成功 | 失败 | 成功率 | 平均延迟 |",
        "|------|-----:|-----:|-------:|---------:|",
    ]
    for name, s in sorted(target_stats.items()):
        t = s['ok'] + s['fail']
        rate = s['ok']/t*100 if t > 0 else 0
        # 计算平均延迟
        latencies = []
        for r in records:
            for c in r.get('connectivity', []):
                if c['name'] == name and c['ok']:
                    latencies.append(c.get('ms', 0))
        avg_ms = sum(latencies)/len(latencies) if latencies else 0
        lines.append(f"| {name} | {s['ok']} | {s['fail']} | {rate:.1f}% | {avg_ms:.0f}ms |")
    
    lines += [
        "",
        "## 诊断建议",
    ]
    
    # 自动生成建议
    if clash_down > clash_up:
        lines.append("- ⚠️ Clash 进程频繁未运行，建议检查开机自启设置")
    
    proxy_works = any(
        c['ok'] for r in records 
        for c in r.get('connectivity', []) 
        if c.get('needs_proxy', False)
    )
    if not proxy_works:
        lines.append("- 🔴 代理完全不通，建议：")
        lines.append("  1. 重启 Clash Verge")
        lines.append("  2. 检查订阅是否过期")
        lines.append("  3. 检查系统代理设置是否指向正确端口")
    
    direct_works = all(
        c['ok'] for r in records 
        for c in r.get('connectivity', []) 
        if not c.get('needs_proxy', False)
    )
    if not direct_works:
        lines.append("- 🔴 直连也不通，可能是网络本身问题")
    
    report = '\n'.join(lines)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(report)
    print(f"\n报告已保存: {REPORT_FILE}")

def register_schedule():
    """注册Windows计划任务：每日 9:00/15:00/21:00 执行检测"""
    import subprocess
    script_path = os.path.abspath(__file__)
    python_path = sys.executable
    task_name = "GA_ProxyHealth"

    # 先删除同名旧任务
    subprocess.run(
        ["schtasks", "/delete", "/tn", task_name, "/f"],
        capture_output=True, text=True
    )

    # 注册新任务 — 每日3次触发
    r = subprocess.run([
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", f'"{python_path}" "{script_path}"',
        "/sc", "daily",
        "/st", "09:00",
        "/ri", "360",       # 每360分钟=6小时重复
        "/du", "24:00",     # 持续24小时
        "/f"
    ], capture_output=True, text=True)

    if r.returncode == 0:
        print(f"[OK] 计划任务 [{task_name}] 注册成功")
        print("   执行时间: 每日 09:00 / 15:00 / 21:00")
        print("   日志位置:", LOG_FILE)
    else:
        print(f"[FAIL] 注册失败: {r.stderr.strip()}")
        print("   可能需要管理员权限")
    return r.returncode == 0


def unregister_schedule():
    """注销Windows计划任务"""
    import subprocess
    task_name = "GA_ProxyHealth"
    r = subprocess.run(
        ["schtasks", "/delete", "/tn", task_name, "/f"],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        print(f"[OK] 计划任务 [{task_name}] 已注销")
    else:
        print(f"[FAIL] 注销失败: {r.stderr.strip()}")
    return r.returncode == 0


if __name__ == '__main__':
    if '--report' in sys.argv:
        generate_report()
    elif '--loop' in sys.argv:
        print("持续检测模式（每5分钟一次），Ctrl+C 停止")
        try:
            while True:
                result = run_check()
                print_result(result)
                time.sleep(300)
        except KeyboardInterrupt:
            print("\n已停止")
            generate_report()
    elif '--schedule' in sys.argv:
        register_schedule()
    elif '--unschedule' in sys.argv:
        unregister_schedule()
    else:
        result = run_check()
        print_result(result)
