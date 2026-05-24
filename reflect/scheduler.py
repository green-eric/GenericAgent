import os, json, time as _time, socket as _socket, logging
from datetime import datetime, timedelta

INTERVAL = 120
ONCE = False

_dir = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(_dir, '../sche_tasks')
DONE  = os.path.join(_dir, '../sche_tasks/done')
_LOG  = os.path.join(_dir, '../sche_tasks/scheduler.log')

# --- 日志（必须在端口锁之前初始化）---
_logger = logging.getLogger('scheduler')
if not _logger.handlers:
    _logger.setLevel(logging.INFO)
    _fh = logging.FileHandler(_LOG, encoding='utf-8')
    _fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s',
                                        datefmt='%Y-%m-%d %H:%M'))
    _logger.addHandler(_fh)

# 端口锁：防止重复启动
# reload时mod.__dict__保留_lock，跳过重复绑定
if '_lock' not in dir():
    _lock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    try:
        _lock.bind(('127.0.0.1', 45762)); _lock.listen(1)
    except OSError:
        _logger.warning('Port 45762 already in use, running without port lock')
        _lock = None

# 默认最大延迟窗口（小时），超过此时间不触发
DEFAULT_MAX_DELAY = 8
_l4_t = 0  # last L4 archive time

def _parse_cooldown(repeat):
    """解析repeat为冷却时间(比实际周期略短,防漂移)"""
    if repeat == 'once': return timedelta(days=999999)
    if repeat in ('daily', 'weekday'): return timedelta(hours=20)
    if repeat == 'weekly': return timedelta(days=6)
    if repeat == 'monthly': return timedelta(days=27)
    if repeat.startswith('every_'):
        try:
            parts = repeat.split('_')
            n = int(parts[1].rstrip('hdm'))
            u = parts[1][-1]
            if u == 'h': return timedelta(hours=n)
            if u == 'm': return timedelta(minutes=n)
            if u == 'd': return timedelta(days=n)
        except (ValueError, IndexError):
            pass  # fall through to warning below
    _logger.warning(f'Unknown repeat type: {repeat}, fallback to 20h cooldown')
    return timedelta(hours=20)

def _last_run(tid, done_files):
    """找最近一次执行时间（优先读.done标记，回退到.md报告）"""
    latest = None
    for df in done_files:
        # 优先: .done 标记文件 (更可靠，触发即写)
        if df.endswith(f'_{tid}.done'):
            try:
                t = datetime.strptime(df[:15], '%Y-%m-%d_%H%M')
                if latest is None or t > latest: latest = t
            except: continue
        # 回退: .md 报告文件 (agentmain执行后写入)
        elif df.endswith(f'_{tid}.md'):
            try:
                t = datetime.strptime(df[:15], '%Y-%m-%d_%H%M')
                if latest is None or t > latest: latest = t
            except: continue
    return latest

def check():
    # L4 archive cron (silent, every 12h)
    global _l4_t
    if _time.time() - _l4_t > 43200:
        _l4_t = _time.time()
        try:
            import sys; sys.path.insert(0, os.path.join(_dir, '../memory/L4_raw_sessions'))
            from compress_session import batch_process
            raw_dir = os.path.join(_dir, '../temp/model_responses')
            r = batch_process(raw_dir, dry_run=False)
            print(f'[L4 cron] {r}')
        except Exception as e:
            _logger.error(f'L4 archive failed: {e}')

    if not os.path.isdir(TASKS): return None
    now = datetime.now()
    os.makedirs(DONE, exist_ok=True)
    done_files = set(os.listdir(DONE))
    for f in sorted(os.listdir(TASKS)):
        if not f.endswith('.json'): continue
        tid = f[:-5]
        try:
            with open(os.path.join(TASKS, f), encoding='utf-8') as fp:
                task = json.loads(fp.read())
        except Exception as e:
            _logger.error(f'JSON parse error for {f}: {e}')
            continue
        if not task.get('enabled', False): continue
        
        repeat = task.get('repeat', 'daily')
        sched = task.get('schedule', '00:00')
        try:
            h, m = map(int, sched.split(':'))
        except Exception as e:
            _logger.error(f'Invalid schedule format in {f}: {sched!r} ({e})')
            continue
        
        # weekday任务：周末跳过
        if repeat == 'weekday' and now.weekday() >= 5: continue
        
        # 还没到schedule时间就跳过
        if now.hour < h or (now.hour == h and now.minute < m): continue
        
        # 执行窗口检查：超过max_delay小时则跳过（防止开机太晚触发过时任务）
        max_delay = task.get('max_delay_hours', DEFAULT_MAX_DELAY)
        sched_minutes = h * 60 + m
        now_minutes = now.hour * 60 + now.minute
        if (now_minutes - sched_minutes) > max_delay * 60:
            _logger.info(f'SKIP {tid}: {now_minutes - sched_minutes}min past schedule, '
                         f'exceeds max_delay={max_delay}h')
            continue
        
        # 检查冷却：直接扫描done目录中匹配的.done文件
        cooldown = _parse_cooldown(repeat)
        last = None
        if os.path.isdir(DONE):
            for df in os.listdir(DONE):
                if df.endswith(f'_{tid}.done') or df.endswith(f'_{tid}.md'):
                    try:
                        t = datetime.strptime(df[:15], '%Y-%m-%d_%H%M')
                        if last is None or t > last: last = t
                    except: pass
        _logger.info(f'COOLDOWN_CHECK {tid}: last={last}, cooldown={cooldown}, now={now}')
        if last and (now - last) < cooldown:
            _logger.info(f'SKIP {tid}: cooling down ({now - last} < {cooldown})')
            continue
        
        # 触发
        _logger.info(f'TRIGGER {tid} (repeat={repeat}, schedule={sched}, '
                     f'last_run={last})')
        ts = now.strftime('%Y-%m-%d_%H%M')
        # 立即写 .done 标记（确保冷却机制生效，即使agentmain没写报告）
        done_marker = os.path.join(DONE, f'{ts}_{tid}.done')
        try:
            with open(done_marker, 'w') as _df:
                _df.write(now.strftime('%Y-%m-%d %H:%M:%S'))
        except OSError as _e:
            _logger.warning(f'Failed to write done marker: {_e}')
        rpt = os.path.join(DONE, f'{ts}_{tid}.md')
        prompt = task.get('prompt', '')
        return (f'[定时任务] {tid}\n'
                f'[报告路径] {rpt}\n\n'
                f'先读 scheduled_task_sop 了解执行流程，然后执行以下任务：\n\n'
                f'{prompt}\n\n'
                f'完成后将执行报告写入 {rpt}。')

    return None

def _list_tasks():
    """列出所有注册任务的状态（用于启动自检）"""
    if not os.path.isdir(TASKS):
        _logger.warning(f'Tasks dir not found: {TASKS}')
        return
    now = datetime.now()
    done_files = set(os.listdir(DONE)) if os.path.isdir(DONE) else set()
    _logger.info(f'=== 注册任务列表 ({now.strftime("%Y-%m-%d %H:%M")}) ===')
    for f in sorted(os.listdir(TASKS)):
        if not f.endswith('.json'): continue
        tid = f[:-5]
        try:
            with open(os.path.join(TASKS, f), encoding='utf-8') as fp:
                task = json.loads(fp.read())
        except Exception as e:
            _logger.error(f'  {tid}: JSON错误 {e}')
            continue
        enabled = task.get('enabled', False)
        repeat = task.get('repeat', 'daily')
        sched = task.get('schedule', '00:00')
        max_delay = task.get('max_delay_hours', DEFAULT_MAX_DELAY)
        last = _last_run(tid, done_files)
        status = '✅ 启用' if enabled else '⏸️ 禁用'
        _logger.info(f'  [{status}] {tid}: {repeat}@{sched} (max_delay={max_delay}h, last_run={last})')
    _logger.info(f'=== 共 {len([f for f in os.listdir(TASKS) if f.endswith(".json")])} 个任务 ===')

def main():
    """主循环：每隔INTERVAL秒执行一次check()，作为Windows服务常驻运行"""
    _logger.info(f'Scheduler started (interval={INTERVAL}s)')
    _list_tasks()
    while True:
        try:
            result = check()
            if result:
                _logger.info(f'Check returned: {result[:80]}...')
            else:
                _logger.debug('Check: no task triggered')
        except Exception as e:
            _logger.error(f'Check error: {e}')
        _time.sleep(INTERVAL)

if __name__ == '__main__':
    main()
