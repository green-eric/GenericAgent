
"""
Auto Git Commit Watcher
监控 D:\GenericAgent 下源码文件变更，自动 git add + commit
"""

import os, sys, time, subprocess, logging
from datetime import datetime

WATCH_ROOT = r"D:\GenericAgent"
COMMIT_INTERVAL = 30
LOG_FILE = os.path.join(WATCH_ROOT, "temp", "auto_git_commit.log")
EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", "L4_raw_sessions"}
EXCLUDE_EXTS = {".pyc", ".pyo", ".bak", ".tmp", ".log"}
EXCLUDE_FILES = {"auto_git_commit.py"}
WATCH_EXTS = {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".bat", ".ps1", ".vbs"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [auto-git] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8", mode="a"),
        logging.StreamHandler(sys.__stdout__),
    ],
)
log = logging.getLogger("auto-git")

def git(*args):
    r = subprocess.run(["git"] + list(args), capture_output=True, text=True, encoding="utf-8", cwd=WATCH_ROOT)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def should_watch(filepath):
    fname = os.path.basename(filepath)
    if fname in EXCLUDE_FILES: return False
    ext = os.path.splitext(fname)[1].lower()
    if ext in EXCLUDE_EXTS: return False
    if ext not in WATCH_EXTS: return False
    parts = os.path.normpath(filepath).split(os.sep)
    for d in EXCLUDE_DIRS:
        if d in parts: return False
    return True

def do_commit():
    out, _, rc = git("status", "--porcelain")
    if rc != 0 or not out: return False
    changed = []
    for line in out.split("\n"):
        line = line.strip()
        if not line: continue
        filepath = line[3:].strip().strip('"')
        fullpath = os.path.join(WATCH_ROOT, filepath)
        if should_watch(fullpath): changed.append(filepath)
    if not changed: return False
    for f in changed: git("add", f)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    files_summary = ", ".join(changed[:5])
    if len(changed) > 5: files_summary += f" +{len(changed)-5}"
    msg = f"[auto] {files_summary} ({ts})"
    _, err, rc = git("commit", "-m", msg)
    if rc == 0:
        log.info(f"✅ {msg}")
        return True
    else:
        log.warning(f"❌ {err}")
        return False

def scan_files():
    files = {}
    for root, dirs, fnames in os.walk(WATCH_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in fnames:
            fullpath = os.path.join(root, fname)
            if should_watch(fullpath):
                try: files[fullpath] = os.path.getmtime(fullpath)
                except OSError: pass
    return files

def main():
    log.info("🚀 Auto Git 启动，监控 %s", WATCH_ROOT)
    last_files = scan_files()
    log.info("   监控 %d 个文件", len(last_files))
    last_change_time = None
    last_commit_time = 0
    try:
        while True:
            time.sleep(5)
            current_files = scan_files()
            changed = False
            for path, mtime in current_files.items():
                if path not in last_files or last_files[path] != mtime:
                    changed = True; break
            if not changed:
                for path in last_files:
                    if path not in current_files:
                        changed = True; break
            last_files = current_files
            if changed:
                last_change_time = time.time()
                log.info("📝 文件变更")
            if last_change_time and (time.time() - last_change_time) >= COMMIT_INTERVAL:
                if do_commit():
                    last_commit_time = time.time()
                    last_change_time = None
    except KeyboardInterrupt:
        log.info("🛑 退出")

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        subprocess.Popen([pythonw, __file__], creationflags=subprocess.CREATE_NO_WINDOW, close_fds=True)
    else:
        main()
