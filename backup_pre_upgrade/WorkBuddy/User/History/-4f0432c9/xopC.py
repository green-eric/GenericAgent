#!/usr/bin/env python3
import sys, time
log_file = sys.argv[1] if len(sys.argv) > 1 else 'run_v5_rerun2.log'
n_lines = int(sys.argv[2]) if len(sys.argv) > 2 else 20
try:
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines[-n_lines:]:
            print(line, end='')
except FileNotFoundError:
    print(f"Log file not found yet: {log_file}")
except Exception as e:
    print(f"Error: {e}")
