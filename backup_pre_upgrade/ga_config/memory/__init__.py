# memory/__init__.py - GA Memory Package
# Enables `import memory` and provides load_memory() convenience.
import os

_MEMDIR = os.path.dirname(os.path.abspath(__file__))


def load_memory() -> dict:
    """Read L2 global_mem.txt and return sections as dict."""
    memfile = os.path.join(_MEMDIR, 'global_mem.txt')
    if not os.path.isfile(memfile):
        return {}
    with open(memfile, 'r', encoding='utf-8') as f:
        content = f.read()
    sections = {}
    current_section = '__head__'
    for line in content.split('\n'):
        if line.startswith('## '):
            current_section = line[3:].strip()
            sections.setdefault(current_section, [])
        else:
            sections.setdefault(current_section, []).append(line)
    return sections


def get_insight() -> str:
    """Read L1 global_mem_insight.txt."""
    with open(os.path.join(_MEMDIR, 'global_mem_insight.txt'), 'r', encoding='utf-8') as f:
        return f.read()