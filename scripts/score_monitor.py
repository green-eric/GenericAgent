#!/usr/bin/env python3
"""
ScoreSys 评分完成监控 + 自动推送到微信
用法:
  python score_monitor.py --check     # 单次检查（由计划任务调用）
  python score_monitor.py --run       # 启动评分并等待完成后推送
  python score_monitor.py --watch     # 持续监控模式
"""
import argparse, os, sys, json, time, subprocess
from pathlib import Path

# === 配置 ===
SCORE_DIR = r"D:\Project\ScoreSys"
REPORT_DIR = os.path.join(SCORE_DIR, "reports")
PENDING_FILE = os.path.join(SCORE_DIR, "pending_wx_report.json")
PUSH_SCRIPT = os.path.join(SCORE_DIR, "push_report.py")
SENT_LOG = os.path.join(SCORE_DIR, "wx_sent_log.json")

def get_latest_report():
    """获取最新的评分报告文件"""
    if not os.path.isdir(REPORT_DIR):
        return None
    files = []
    for f in os.listdir(REPORT_DIR):
        fp = os.path.join(REPORT_DIR, f)
        if os.path.isfile(fp) and f.endswith((".json", ".html", ".xlsx", ".csv")):
            files.append((os.path.getmtime(fp), fp))
    if not files:
        return None
    files.sort(reverse=True)
    return files[0][1]

def get_sent_reports():
    """获取已推送的报告列表"""
    if os.path.exists(SENT_LOG):
        try:
            return set(json.loads(open(SENT_LOG).read()))
        except:
            pass
    return set()

def mark_sent(report_path):
    """标记报告已推送"""
    sent = get_sent_reports()
    sent.add(report_path)
    with open(SENT_LOG, "w") as f:
        json.dump(list(sent), f)

def check_and_push():
    """检查是否有新报告需要推送"""
    latest = get_latest_report()
    if not latest:
        print("[Monitor] 未找到评分报告")
        return False
    
    sent = get_sent_reports()
    if latest in sent:
        print(f"[Monitor] 报告已推送过: {os.path.basename(latest)}")
        return False
    
    print(f"[Monitor] 发现新报告: {os.path.basename(latest)}")
    
    # 调用 push_report.py 推送
    result = subprocess.run(
        [sys.executable, PUSH_SCRIPT, latest],
        capture_output=True, text=True, timeout=60
    )
    output = result.stdout.strip()
    print(f"[Monitor] push_report 输出: {output}")
    
    if result.returncode == 0 and ("成功" in output or "SUCCESS" in output or "pushed" in output.lower()):
        mark_sent(latest)
        print(f"[Monitor] 推送成功 ✅")
        return True
    else:
        print(f"[Monitor] 推送可能失败: {result.stderr.strip()}")
        # 也标记为已推送，避免重复推送
        mark_sent(latest)
        return True

def run_score_and_push():
    """启动评分并等待完成后推送"""
    print("[Monitor] 启动 ScoreSys 评分...")
    main_py = os.path.join(SCORE_DIR, "main.py")
    result = subprocess.run(
        [sys.executable, main_py],
        cwd=SCORE_DIR, timeout=3600
    )
    print(f"[Monitor] 评分完成, returncode={result.returncode}")
    if result.returncode == 0:
        check_and_push()
    else:
        # 评分失败也通知
        _notify_failure(result.returncode)
    return result.returncode

def _notify_failure(code):
    """评分失败时通知"""
    try:
        sys.path.insert(0, r"D:\GenericAgent\frontends")
        sys.path.insert(0, r"D:\GenericAgent")
        from wechatapp import WxBotClient, USER_ID
        client = WxBotClient()
        client.send_text(USER_ID, f"⚠️ ScoreSys 评分失败\n返回码: {code}\n时间: {time.strftime('%Y-%m-%d %H:%M')}\n请检查日志")
    except Exception as e:
        print(f"[Monitor] 失败通知发送异常: {e}")

def watch_loop(interval=60):
    """持续监控模式"""
    print(f"[Monitor] 启动持续监控, 间隔 {interval}s")
    while True:
        try:
            check_and_push()
        except Exception as e:
            print(f"[Monitor] 检查异常: {e}")
        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ScoreSys 评分监控推送")
    parser.add_argument("--check", action="store_true", help="单次检查")
    parser.add_argument("--run", action="store_true", help="启动评分+推送")
    parser.add_argument("--watch", action="store_true", help="持续监控")
    parser.add_argument("--interval", type=int, default=60, help="监控间隔(秒)")
    args = parser.parse_args()
    
    if args.run:
        sys.exit(run_score_and_push())
    elif args.watch:
        watch_loop(args.interval)
    else:
        # 默认 --check 模式
        found = check_and_push()
        sys.exit(0 if found else 1)
