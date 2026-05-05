"""
Restore User Patches
GA 更新后恢复用户自定义调整

用法:
  python restore_patches.py              # 查看状态
  python restore_patches.py --update     # 同步上游更新 + 恢复补丁
  python restore_patches.py --cherry     # 仅 cherry-pick user-patches 的提交
"""

import os, sys, subprocess, argparse

WATCH_ROOT = r"D:\GenericAgent"
UPSTREAM = "upstream"
ORIGIN = "origin"
MAIN_BRANCH = "main"
PATCH_BRANCH = "user-patches"

def git(*args):
    r = subprocess.run(["git"] + list(args), capture_output=True, text=True, encoding="utf-8", cwd=WATCH_ROOT)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def run_cmd(desc, *args):
    print(f"\n{'='*50}")
    print(f"📌 {desc}")
    print(f"   git {' '.join(args)}")
    out, err, rc = git(*args)
    if rc == 0:
        print(f"   ✅ OK")
        if out: print(f"   {out[:200]}")
    else:
        print(f"   ❌ FAILED: {err[:200]}")
    return rc

def status():
    print("="*50)
    print("📊 当前状态")
    out, _, _ = git("branch", "-vv")
    print(f"\n分支:\n{out}")
    out, _, _ = git("log", "--oneline", "--graph", "--all", "-15")
    print(f"\n提交历史:\n{out}")
    out, _, _ = git("status", "--short")
    print(f"\n工作区:\n{out if out else '(clean)'}")
    out, _, rc = git("log", f"{MAIN_BRANCH}..{PATCH_BRANCH}", "--oneline")
    if rc == 0 and out:
        count = len(out.strip().split('\n'))
        print(f"\n📝 {PATCH_BRANCH} 上有 {count} 个提交未合入 {MAIN_BRANCH}:")
        for line in out.strip().split('\n'):
            print(f"   {line}")
    else:
        print(f"\n✅ {PATCH_BRANCH} 的所有提交已合入 {MAIN_BRANCH}")

def update():
    """同步上游更新并恢复补丁"""
    run_cmd("暂存工作区变更", "stash", "push", "-m", "auto-stash before update")
    run_cmd("切换到 main", "checkout", MAIN_BRANCH)
    run_cmd("拉取上游更新", "fetch", UPSTREAM)
    run_cmd("合并上游更新", "merge", f"{UPSTREAM}/{MAIN_BRANCH}")
    run_cmd("推送到 origin/main", "push", ORIGIN, MAIN_BRANCH)
    print(f"\n{'='*50}")
    print(f"📌 Cherry-pick {PATCH_BRANCH} 的提交")
    out, _, rc = git("log", f"{MAIN_BRANCH}..{PATCH_BRANCH}", "--oneline", "--reverse")
    if rc != 0 or not out:
        print(f"   ℹ️ 没有需要 cherry-pick 的提交")
    else:
        commits = [line.split()[0] for line in out.strip().split('\n') if line.strip()]
        print(f"   共 {len(commits)} 个提交")
        for sha in commits:
            _, err2, rc2 = git("cherry-pick", sha)
            if rc2 == 0:
                print(f"   ✅ {sha[:8]} OK")
            else:
                print(f"   ⚠️ {sha[:8]} 冲突，请手动解决后 git cherry-pick --continue")
                return False
    run_cmd(f"切换到 {PATCH_BRANCH}", "checkout", PATCH_BRANCH)
    run_cmd(f"rebase", "rebase", MAIN_BRANCH)
    run_cmd(f"推送 {PATCH_BRANCH}", "push", ORIGIN, PATCH_BRANCH, "--force-with-lease")
    run_cmd("恢复工作区", "stash", "pop")
    print(f"\n{'='*50}")
    print("✅ GA 更新完成，用户补丁已恢复！")
    return True

def cherry_only():
    run_cmd("切换到 main", "checkout", MAIN_BRANCH)
    out, _, rc = git("log", f"{MAIN_BRANCH}..{PATCH_BRANCH}", "--oneline", "--reverse")
    if rc != 0 or not out:
        print("ℹ️ 没有需要 cherry-pick 的提交")
        return
    commits = [line.split()[0] for line in out.strip().split('\n') if line.strip()]
    for sha in commits:
        _, err2, rc2 = git("cherry-pick", sha)
        if rc2 == 0:
            print(f"✅ {sha[:8]} OK")
        else:
            print(f"⚠️ {sha[:8]} 冲突")
            return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GA 更新后恢复用户补丁")
    parser.add_argument("--update", action="store_true", help="同步上游更新 + 恢复补丁")
    parser.add_argument("--cherry", action="store_true", help="仅 cherry-pick")
    args = parser.parse_args()
    os.chdir(WATCH_ROOT)
    if args.update:
        update()
    elif args.cherry:
        cherry_only()
    else:
        status()
