#!/usr/bin/env python3
"""Proxy Health 7-Day Stability Report Generator"""
import json, os, sys
from datetime import datetime, timedelta

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), r"temp\\proxy_logs\\proxy_health.jsonl")
REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), r"temp\\autonomous_reports")

def generate_report():
    if not os.path.exists(LOG_FILE):
        print("No log file found")
        return

    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        records = []
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except:
                    pass

    if not records:
        print("No records found")
        return

    # 统计
    now = datetime.now()
    cutoff = now - timedelta(days=7)
    recent = [r for r in records if datetime.fromisoformat(r['ts']) >= cutoff]

    total = len(recent)
    if total == 0:
        print("No recent records in 7 days")
        return

    # 连通性统计
    conn_stats = {}
    port_stats = {}
    clash_up_count = 0

    for r in recent:
        if r.get('clash_processes'):
            clash_up_count += 1
        for port, ok in r.get('ports', {}).items():
            if port not in port_stats:
                port_stats[port] = {'up': 0, 'down': 0}
            if ok:
                port_stats[port]['up'] += 1
            else:
                port_stats[port]['down'] += 1
        for c in r.get('connectivity', []):
            name = c['name']
            if name not in conn_stats:
                conn_stats[name] = {'ok': 0, 'fail': 0, 'avg_ms': 0, 'ms_list': []}
            if c['ok']:
                conn_stats[name]['ok'] += 1
                if c.get('ms'):
                    conn_stats[name]['ms_list'].append(c['ms'])
            else:
                conn_stats[name]['fail'] += 1

    # 生成报告
    report_lines = []
    report_lines.append("# Proxy Health 7-Day Stability Report")
    report_lines.append(f"\\nGenerated: {now.strftime('%Y-%m-%d %H:%M')}")
    report_lines.append(f"Period: Last 7 days ({cutoff.strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')})")
    report_lines.append(f"Total checks: {total}")
    report_lines.append(f"\\n## Clash Process Uptime")
    report_lines.append(f"- Up: {clash_up_count}/{total} ({clash_up_count/total*100:.1f}%)")
    report_lines.append(f"\\n## Port Availability")
    for port, stats in sorted(port_stats.items()):
        uptime = stats['up']/(stats['up']+stats['down'])*100 if (stats['up']+stats['down']) > 0 else 0
        report_lines.append(f"- Port {port}: {uptime:.1f}% ({stats['up']}/{stats['up']+stats['down']})")
    report_lines.append(f"\\n## Connectivity")
    for name, stats in sorted(conn_stats.items()):
        total_c = stats['ok'] + stats['fail']
        rate = stats['ok']/total_c*100 if total_c > 0 else 0
        avg_ms = sum(stats['ms_list'])/len(stats['ms_list']) if stats['ms_list'] else 0
        report_lines.append(f"- {name}: {rate:.1f}% success, avg {avg_ms:.0f}ms")
    report_lines.append(f"\\n## Summary")
    all_ok = sum(1 for r in recent if all(c['ok'] for c in r.get('connectivity', []) if c['name'] != 'Clash API'))
    report_lines.append(f"- All-clear checks: {all_ok}/{total} ({all_ok/total*100:.1f}%)")

    report_path = os.path.join(REPORT_DIR, f"R157_proxy_health_7day_{now.strftime('%Y%m%d')}.md")
    os.makedirs(REPPORT_DIR, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\\n'.join(report_lines))
    print(f"Report saved: {report_path}")

if __name__ == '__main__':
    generate_report()
