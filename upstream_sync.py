#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GA 上游代码自动同步工具
======================
检测 upstream/main 的新提交，按风险分类：
  ✅ 安全 — 纯文档/配置/测试，可直接 merge
  ⚠️ 需审查 — 核心逻辑修改，需人工确认
  ❌ 跳过 — 冲突风险高或当前分支已包含
"""

import sys, os, io, subprocess, json, re, argparse
from datetime import datetime
from typing import List, Dict, Tuple

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

GA_DIR = r"D:\GenericAgent"
REPORT_DIR = os.path.join(GA_DIR, "autonomous_reports")

# 确保 git 输出用 UTF-8 解码
_GIT_ENV = os.environ.copy()
_GIT_ENV["GIT_PYTHON_REFRESH"] = "quiet"
_GIT_ENV["LC_ALL"] = "C.UTF-8"


def run_git(args: List[str], cwd=GA_DIR, check=False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
        check=check,
        env=_GIT_ENV,
    )


def fetch_upstream() -> bool:
    r = run_git(["fetch", "upstream"])
    return r.returncode == 0


def get_new_commits(branch, upstream) -> List[Dict]:
    r = run_git(["log", f"{branch}..{upstream}", "--no-merges", "--format=%H|%s|%an|%ad", "--date=short"])
    commits = []
    for line in r.stdout.strip().split("\n"):
        if "|" not in line:
            continue
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue
        commits.append({
            "hash": parts[0][:8],
            "subject": parts[1],
            "author": parts[2],
            "date": parts[3],
            "full_hash": parts[0],
        })
    return commits


def get_commit_files(commit_hash: str) -> List[str]:
    r = run_git(["diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash])
    return [f for f in r.stdout.strip().split("\n") if f]


def classify_commit(commit: Dict, files: List[str]) -> Tuple[str, str]:
    subject = commit["subject"].lower()
    fname_str = " ".join(files).lower()

    # 冲突高风险: 核心源码
    core_files = ["agentmain.py", "llmcore", "task_planning", "supervisor", "goal_mode"]
    # 安全: 文档/配置/测试
    safe_files = ["readme", "changelog", "license", ".gitignore", "test_", "_test.py", "docs/"]
    # 前端/桌面
    ui_files = ["frontend", "static/", ".css", ".html", ".js", "tauri", "desktop", "style"]

    has_core = any(p in fname_str for p in core_files)
    has_safe = any(p in fname_str for p in safe_files)
    has_ui = any(p in fname_str for p in ui_files)

    if has_safe:
        return ("safe", "文档/配置/测试，安全可合并")
    if has_ui:
        return ("safe", "前端/UI 变更，不影响核心逻辑")
    if "chore" in subject or "docs" in subject or "style" in subject:
        return ("safe", "杂务/文档变更")
    if "refactor" in subject and not has_core:
        return ("safe", "非核心重构，风险较低")
    if has_core and ("refactor" in subject or "fix" in subject):
        return ("review", "核心代码修改，需人工审查")
    if has_core:
        return ("skip", "核心代码变更，风险较高")
    if "fix" in subject:
        return ("review", "修复类提交，需确认影响范围")

    return ("review", "需人工判断")


def generate_report(commits: List[Dict], classifications: Dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    safe = [(c, classifications[c["hash"]]) for c in commits if classifications[c["hash"]][0] == "safe"]
    review = [(c, classifications[c["hash"]]) for c in commits if classifications[c["hash"]][0] == "review"]
    skip = [(c, classifications[c["hash"]]) for c in commits if classifications[c["hash"]][0] == "skip"]

    lines = []
    lines.append(f"# GA 上游同步报告 — {now}")
    lines.append("")
    lines.append("## 概览")
    lines.append(f"- 上游新提交: **{len(commits)}** 个")
    lines.append(f"- ✅ 安全可合并: **{len(safe)}** 个")
    lines.append(f"- ⚠️ 需审查: **{len(review)}** 个")
    lines.append(f"- ❌ 跳过: **{len(skip)}** 个")
    lines.append("")

    if safe:
        lines.append("## ✅ 安全可合并")
        lines.append("")
        lines.append("| # | 提交 | 作者 | 日期 | 原因 |")
        lines.append("|---|------|------|------|------|")
        for i, (c, (cat, reason)) in enumerate(safe, 1):
            lines.append(f"| {i} | `{c['hash']}` {c['subject']} | {c['author']} | {c['date']} | {reason} |")
        lines.append("")

    if review:
        lines.append("## ⚠️ 需审查")
        lines.append("")
        lines.append("| # | 提交 | 作者 | 日期 | 原因 |")
        lines.append("|---|------|------|------|------|")
        for i, (c, (cat, reason)) in enumerate(review, 1):
            files = get_commit_files(c["full_hash"])
            file_list = ", ".join(files[:5])
            if len(files) > 5:
                file_list += "..."
            lines.append(f"| {i} | `{c['hash']}` {c['subject']} | {c['author']} | {c['date']} | {reason} |")
            lines.append(f"| | 文件: `{file_list}` | | | |")
        lines.append("")

    if skip:
        lines.append("## ❌ 跳过")
        lines.append("")
        for c, (cat, reason) in skip:
            lines.append(f"- `{c['hash']}` {c['subject']} — {reason}")
        lines.append("")

    if safe:
        lines.append("## 操作建议")
        lines.append("")
        hashes = " ".join(c["full_hash"] for c, _ in safe)
        lines.append("```bash")
        lines.append(f"# 合并安全提交:")
        lines.append(f"cd {GA_DIR}")
        lines.append(f"git cherry-pick {hashes}")
        lines.append("```")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="GA 上游代码同步检测")
    parser.add_argument("--branch", default="user-patches", help="当前分支")
    parser.add_argument("--upstream", default="upstream/main", help="上游分支")
    parser.add_argument("--no-fetch", action="store_true", help="跳过 fetch")
    parser.add_argument("--report-only", action="store_true", help="只输出到控制台")
    args = parser.parse_args()

    if not args.no_fetch:
        print("🔄 正在 fetch 上游...")
        if not fetch_upstream():
            print("❌ fetch 失败，检查网络或代理")
            sys.exit(1)
        print("✅ fetch 成功")

    commits = get_new_commits(args.branch, args.upstream)
    if not commits:
        print("✅ 无新提交，已是最新")
        return

    print(f"📋 发现 {len(commits)} 个新提交，正在分类...")
    classifications = {}
    for c in commits:
        files = get_commit_files(c["full_hash"])
        cat, reason = classify_commit(c, files)
        classifications[c["hash"]] = (cat, reason)
        icon = {"safe": "✅", "review": "⚠️", "skip": "❌"}[cat]
        print(f"  {icon} {c['hash']} {c['subject'][:60]}")

    report = generate_report(commits, classifications)

    if not args.report_only:
        os.makedirs(REPORT_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        report_path = os.path.join(REPORT_DIR, f"upstream_sync_{ts}.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n📄 报告已保存: {report_path}")

    print("\n" + report)


if __name__ == "__main__":
    main()
