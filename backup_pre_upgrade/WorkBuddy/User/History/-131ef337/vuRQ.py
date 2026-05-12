#!/usr/bin/env python3
"""Fix main.py indentation"""
with open(r'd:\Project\ScoreSys\main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and fix the evaluate_one function
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Fix the finally block indentation
    if 'finally: semaphore.release();' in line:
        new_lines.append('        finally:\n')
        new_lines.append('            semaphore.release()\n')
        # Skip the old if not mock line that was on same line
        if 'if not mock: time.sleep(rate_limit)' in line:
            new_lines.append('            if not mock:\n')
            new_lines.append('                time.sleep(rate_limit)\n')
        i += 1
        continue
    # Fix evaluate_one function definition indentation
    if 'def evaluate_one(code, name_from_pool):' in line and not line.startswith('    '):
        new_lines.append('    def evaluate_one(code, name_from_pool):\n')
        i += 1
        continue
    # Fix semaphore.acquire() indentation
    if 'semaphore.acquire()' in line and not line.strip().startswith('#'):
        if 'def evaluate_one' not in line:
            new_lines.append('        semaphore.acquire()\n')
            i += 1
            continue
    # Fix try: indentation
    if line.strip() == 'try:' and 'def evaluate_one' not in lines[max(0,i-1)]:
        new_lines.append('        try:\n')
        i += 1
        continue
    # Fix with lock: indentation
    if 'with lock:' in line and 'results.append' in line:
        new_lines.append('            with lock:\n')
        new_lines.append('                results.append(res)\n')
        # Skip next line if it's the print progress
        i += 1
        if i < len(lines) and 'print(f"' in lines[i] and '总分' in lines[i]:
            new_lines.append('                ' + lines[i].lstrip())
            i += 1
        continue
    # Fix return 'ok' indentation
    if line.strip() == "return 'ok'":
        new_lines.append("            return 'ok'\n")
        i += 1
        continue
    new_lines.append(line)
    i += 1

with open(r'd:\Project\ScoreSys\main.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Fixed indentation')
