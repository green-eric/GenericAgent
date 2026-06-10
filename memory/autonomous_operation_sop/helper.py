"""
autonomous_task.py - 自主行动任务管理API
放置: memory/autonomous_operation_sop/
用法: import autonomous_task (或 from autonomous_operation_sop import autonomous_task)

4个函数:
  get_todo()        → 返回TODO内容
  get_history(n)    → 返回最近n条历史
  complete_task()   → 移报告+编号+写history+返回改TODO指令
  set_todo()        → 返回TODO真实路径
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime

# ── 路径计算（基于模块自身位置） ──
_MODULE_DIR = Path(__file__).resolve().parent          # memory/autonomous_operation_sop/
_MEMORY_DIR = _MODULE_DIR.parent                       # memory/
_AGENT_DIR = _MEMORY_DIR.parent                        # GenericAgent/
_TEMP_DIR = _AGENT_DIR / "temp"                        # GenericAgent/temp/
_REPORTS_DIR = _TEMP_DIR / "autonomous_reports"
_HISTORY_FILE = _REPORTS_DIR / "history.txt"
_TODO_FILE = _TEMP_DIR / "TODO.txt"

def _next_report_number() -> int:
    """扫 history.txt 第一行提取最大 RXX 编号，返回下一个"""
    if not _HISTORY_FILE.exists():
        return 1
    with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    # 匹配所有 R 后跟数字的模式
    nums = [int(m) for m in re.findall(r'R(\d+)', content)]
    if not nums:
        return 1
    return max(nums) + 1


def get_todo() -> str:
    """返回 TODO.txt 的内容。若文件不存在返回提示。"""
    if not _TODO_FILE.exists(): return f"[autonomous_task] TODO.txt 不存在，路径: {_TODO_FILE}"
    with open(_TODO_FILE, "r", encoding="utf-8") as f: return f.read()

def get_history(n: int = 20) -> str:
    """返回 history.txt 的前 n 行（最新在前）。"""
    if not _HISTORY_FILE.exists():
        return f"[autonomous_task] history.txt 不存在，路径: {_HISTORY_FILE}"
    with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return "".join(lines[:n])


def set_todo(content: str = None) -> str:
    """
    将 content 写入 TODO.txt。若 content 为空则返回当前内容。
    返回值: 写入确认或当前TODO内容。
    """
    if content is None:
        return get_todo()
    with open(_TODO_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    return f"✅ TODO已写入: {_TODO_FILE}"


def complete_task(taskname: str, historyline: str, report_path: str) -> str:
    """
    完成任务的原子操作：
    1. 移动 report_path → autonomous_reports/R{XX}_{taskname}.md（自动编号）
    2. prepend historyline 到 history.txt（校验必须单行）
    3. 返回字符串指示 agent 自己去改 TODO
    Args:
        taskname: 任务简短名称（用于报告文件名，如 "晨间简报"）
        historyline: 历史记录内容（必须单行，日期自动添加，如 "工程 | 晨间简报 | 完成7模块聚合"）
        report_path: agent 已写好的报告文件路径（绝对或相对于cwd）
    Returns:
        成功消息 + 改TODO指令，或错误消息
    """
    errors = []

    # ── 校验 ──
    if "\n" in historyline.strip():
        return "[ERROR] historyline 必须是单行，不能包含换行符"

    report = Path(report_path).resolve()
    if not report.exists():
        return f"[ERROR] 报告文件不存在: {report_path}"

    if not _REPORTS_DIR.exists():
        _REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. 移动报告 ──
    rnum = _next_report_number()
    # 清理 taskname 中的非法文件名字符
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', taskname).strip()
    dest_name = f"R{rnum}_{safe_name}.md"
    dest_path = _REPORTS_DIR / dest_name

    try:
        shutil.move(str(report), str(dest_path))
    except Exception as e:
        return f"[ERROR] 移动报告失败: {e}"

    # ── 2. prepend history ──
    # 自动加编号 + 日期（剥离 agent 可能已写的编号/日期，统一重建）
    line = historyline.strip()
    line = re.sub(r'^R\d+\s*\|\s*', '', line)           # 剥离 R 编号
    line = re.sub(r'^\d{4}-\d{2}-\d{2}\s*\|\s*', '', line)  # 剥离日期
    today = datetime.now().strftime('%Y-%m-%d')
    line = f"R{rnum} | {today} | {line}"

    try:
        existing = ""
        if _HISTORY_FILE.exists():
            with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
                existing = f.read()
        with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
            f.write(line + "\n" + existing)
    except Exception as e:
        # 回滚：把报告移回去
        try:
            shutil.move(str(dest_path), str(report))
        except:
            pass
        return f"[ERROR] 写入 history 失败: {e}（报告已回滚）"

    # ── 3. 返回改 TODO 指令 ──
    return (
        f"✅ 完成！报告已保存: {dest_name}\n"
        f"历史已记录: {line}\n"
        f"👉 请在 {_TODO_FILE} 中将对应任务标记为 [x] R{rnum}，然后结束，**其他TODO下次再干**"
    )




# ═══════════════════════════════════════════════
# 新增辅助函数 (R411)
# ═══════════════════════════════════════════════

def list_tasks():
    """
    解析 TODO.txt 返回结构化任务列表。
    返回 dict: { 'total': int, 'done': int, 'pending': int, 'blocked': int,
                  'items': [ { 'id': str, 'name': str, 'status': str, 'value': int }, ... ] }
    """
    if not _TODO_FILE.exists():
        return {"total": 0, "done": 0, "pending": 0, "blocked": 0, "items": []}

    tasks = []
    done = pending = blocked = 0
    with open(_TODO_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        # 匹配 [x] 或 [ ] 或 ❌ 条目标
        m = re.search(r'\[([ xX])\]?\s*(?:[🔥🥇🥈🥉]?\s*)?(\d+|[①②③④⑤⑥⑦⑧⑨⑩])\s*[.．、]?\s*(.+?)\s*\|', line)
        if m:
            status_char = m.group(1).lower() if m.group(1) in ('x', ' ',) else ' '
            id_raw = m.group(2)
            name = m.group(3).strip()
            # 中文数字转阿拉伯
            cn_map = {'①':'1','②':'2','③':'3','④':'4','⑤':'5','⑥':'6','⑦':'7','⑧':'8','⑨':'9','⑩':'10'}
            task_id = cn_map.get(id_raw, id_raw)
            item_status = 'done' if status_char == 'x' else 'blocked' if '阻塞' in line else 'pending'
            if item_status == 'done': done += 1
            elif item_status == 'blocked': blocked += 1
            else: pending += 1
            # 提取价值
            val_m = re.search(r'价值(\d+)', line)
            value = int(val_m.group(1)) if val_m else 0
            tasks.append({"id": task_id, "name": name, "status": item_status, "value": value})

    return {
        "total": len(tasks), "done": done,
        "pending": pending, "blocked": blocked, "items": tasks
    }


def report_stats():
    """
    TODO 统计报告。返回多行字符串。
    """
    data = list_tasks()
    if data['total'] == 0:
        return "📊 TODO 统计: 无任务数据"
    done_pct = round(data['done'] / data['total'] * 100)
    vals = [t['value'] for t in data['items']]
    avg_val = round(sum(vals) / len(vals), 1) if vals else 0
    lines = [
        f"📊 TODO 统计 ({data['total']}条)",
        f"● 已完成: {data['done']} ({done_pct}%)",
        f"● 待执行: {data['pending']}",
        f"● 阻塞:   {data['blocked']}",
        f"● 平均价值: {avg_val}",
    ]
    if data['pending'] > 0:
        next_task = [t for t in data['items'] if t['status'] == 'pending']
        if next_task:
            lines.append(f"● 下一条: #{next_task[0]['id']} {next_task[0]['name']} (价值{next_task[0]['value']})")
    return '\n'.join(lines)


def get_next_todo():
    """
    返回下一条可执行的未完成TODO的文本行。
    跳过阻塞/已取消/已移除/冻结/已验收/已删除条目。
    若无未完成，返回 None。
    """
    if not _TODO_FILE.exists():
        return None
    skip_kw = ['阻塞', '已取消', '已移除', '已删除', '已验收', '冻结', '❌', '~~']
    with open(_TODO_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if re.search(r'\[\s\]', line) and not any(kw in line for kw in skip_kw):
                return line.strip()
    return None


# ── 快速自检 ──
if __name__ == "__main__":
    print(f"TEMP_DIR:    {_TEMP_DIR}")
    print(f"REPORTS_DIR: {_REPORTS_DIR}")
    print(f"HISTORY:     {_HISTORY_FILE}")
    print(f"TODO:        {_TODO_FILE}")
    print(f"Next R#:     R{_next_report_number()}")
    print(f"\n--- TODO ---\n{get_todo()[:200]}")
    print(f"\n--- History (5) ---\n{get_history(5)}")
    print(f"\n--- list_tasks() ---")
    import json; print(json.dumps(list_tasks(), ensure_ascii=False, indent=2))
    print(f"\n--- report_stats() ---")
    print(report_stats())
    print(f"\n--- get_next_todo() ---")
    print(get_next_todo())