#!/usr/bin/env python3
"""把官方包全量落到官方分支（main）上，并精确暂存。

这一步是整个升级里最容易出错的机械环节，所以做成脚本而不是手打命令：

1. "全量替换"必须先删掉 main 上已跟踪的旧文件，否则官方删掉的文件会残留成幽灵文件。
2. 但 .gitignore 这类本地基建文件不能删 —— 官方包里根本没有它。
3. 绝对不能用 `git add -A` 暂存：main 上的 .gitignore 往往非常简陋（可能只有三行），
   不覆盖 __pycache__/.DS_Store/.venv，`git add -A` 会把这些垃圾一起提交进去。
   正确做法是 `git add -u`（只处理已跟踪文件的改动与删除）+ 按官方文件清单显式 add 新增文件。

用法:
    python3 apply_official.py --package ~/Downloads/xxx_v2.1.0 [--preserve .gitignore] [--dry-run]
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from file_inventory import package_inventory

NOISE = {".git", "__pycache__", ".DS_Store", ".venv", "venv", ".idea", ".vscode",
         ".pytest_cache", ".ruff_cache", ".mypy_cache", "node_modules", ".ipynb_checkpoints"}
JUNK_HINT = ("__pycache__", ".DS_Store", ".venv/", ".idea/", ".vscode/", ".pyc")


def run(args, cwd=None, check=True):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"命令失败 {' '.join(map(str, args))}\n{r.stderr}")
    return r.stdout


def git(repo, *args, check=True):
    return run(["git", "-C", str(repo), "-c", "core.quotePath=false", *args], check=check)


def runtime_tops(repo, pkg):
    """官方包里被 git 忽略的顶层目录 = 运行时数据目录，不参与代码替换。

    判定交给 `git check-ignore`，且只针对官方包真实存在的目录。自己解析 .gitignore
    会踩坑：很多仓库用完整的 Python 模板 gitignore（含 docs/ lib/ build/ private/ 等上百条），
    自行解析会把这些全当运行时目录，官方包一旦真带了同名目录就会被静默跳过、代码丢失。
    """
    tops = [p.name for p in Path(pkg).iterdir() if p.is_dir() and p.name not in NOISE]
    if not tops:
        return set()
    r = subprocess.run(["git", "-C", str(repo), "check-ignore", "--", *[t + "/" for t in tops]],
                       capture_output=True, text=True)
    return {line.strip().rstrip("/") for line in r.stdout.splitlines() if line.strip()}


def official_files(pkg, skip_tops):
    """官方包里的代码文件（相对路径），排除噪音与运行时数据目录。"""
    out = []
    pkg = Path(pkg)
    for dirpath, dirnames, filenames in os.walk(pkg):
        dirnames[:] = [d for d in dirnames if d not in NOISE]
        rel_dir = Path(dirpath).relative_to(pkg)
        top = rel_dir.parts[0] if rel_dir.parts else ""
        if top and top in skip_tops:
            dirnames[:] = []
            continue
        for fn in filenames:
            if fn in NOISE:
                continue
            out.append(str(rel_dir / fn) if rel_dir.parts else fn)
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--package", required=True)
    ap.add_argument("--preserve", nargs="*", default=[".gitignore"],
                    help="官方包里没有、但必须留在 main 上的本地基建文件")
    ap.add_argument("--runtime-data", choices=["copy", "skip"], default="skip",
                    help="是否把官方包里位于 gitignore 目录下的运行时数据也复制进工作区（会先备份）")
    ap.add_argument("--backup-dir", help="运行时数据备份目录（配合 --runtime-data copy）")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    repo = Path(run(["git", "-C", a.repo, "rev-parse", "--show-toplevel"]).strip())
    pkg = Path(a.package).expanduser().resolve()
    if not pkg.is_dir():
        print(f"错误：官方包不存在 {pkg}", file=sys.stderr)
        return 2

    backup = None
    if a.runtime_data == "copy":
        if not a.backup_dir:
            ap.error("--runtime-data copy 必须提供 --backup-dir；不会无备份覆盖运行时数据")
        backup = Path(a.backup_dir).expanduser().resolve()
        if backup == repo or repo in backup.parents or backup == pkg or pkg in backup.parents:
            ap.error("--backup-dir 必须位于仓库和官方包之外")
        if backup.exists() and (not backup.is_dir() or any(backup.iterdir())):
            ap.error("--backup-dir 必须是新目录或空目录，不能覆盖已有备份")

    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    if branch not in ("main", "master"):
        print(f"错误：当前在 '{branch}'，全量替换只能在官方分支(main/master)上做。", file=sys.stderr)
        return 2

    dirty = [l for l in git(repo, "status", "--porcelain").splitlines()
             if l.strip() and not any(h in l for h in JUNK_HINT)]
    if dirty:
        print("错误：工作区有未提交改动，先处理干净再来：", file=sys.stderr)
        print("\n".join(dirty), file=sys.stderr)
        return 2

    skip = runtime_tops(repo, pkg)
    off, runtime_files = package_inventory(repo, pkg)
    tracked = [l for l in git(repo, "ls-tree", "-r", "--name-only", branch).splitlines() if l.strip()]
    preserve = set(a.preserve)
    to_delete = [f for f in tracked if f not in preserve]

    print(f"仓库        {repo}  (分支 {branch})")
    print(f"官方包      {pkg}")
    print(f"运行时目录  {sorted(skip) or '无'}  ← 顶层提示；实际逐文件分类，已跟踪参考文件仍参与更新")
    print(f"将删除旧的已跟踪文件 {len(to_delete)} 个，保留 {sorted(preserve)}")
    print(f"将写入官方跟踪文件 {len(off)} 个；另有未跟踪且被忽略的运行时文件 {len(runtime_files)} 个")
    if a.dry_run:
        print("\n[dry-run] 未做任何修改。")
        return 0

    # 在删除代码或覆盖数据之前，完成全部旧运行时文件的备份；备份失败直接停止。
    if backup is not None:
        backup.mkdir(parents=True, exist_ok=True)
        for rel in runtime_files:
            old = repo / rel
            if old.exists() or old.is_symlink():
                b = backup / rel
                b.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(old, b)

    # 1) 删掉旧的已跟踪文件 —— 只删 git 跟踪的，未跟踪的本地文件不碰
    for f in to_delete:
        p = repo / f
        if p.exists() or p.is_symlink():
            p.unlink()

    # 2) 写入官方代码
    for rel in off:
        src, dst = pkg / rel, repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # 3) 只清理本次删除文件的祖先目录，不遍历/删除无关的运行时空目录。
    cleanup = set()
    for rel in to_delete:
        if Path(rel).parts[0] in skip or any(part in NOISE for part in Path(rel).parts):
            continue
        parent = (repo / rel).parent
        while parent != repo:
            cleanup.add(parent)
            parent = parent.parent
    for p in sorted(cleanup, key=lambda p: len(p.parts), reverse=True):
        if p.is_dir() and not p.is_symlink() and not any(p.iterdir()):
            p.rmdir()

    # 4) 运行时数据（最小下单量表、币种列表这类不进 git 但影响运行的文件）
    copied_runtime = []
    if a.runtime_data == "copy":
        for rel in runtime_files:
            dst = repo / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pkg / rel, dst)
            copied_runtime.append(rel)

    # 5) 精确暂存：git add -u 处理已跟踪文件的改动/删除，再按清单显式 add 新增
    git(repo, "add", "-u")
    for rel in off:
        git(repo, "add", "-f", "--", rel)
    for rel in preserve:
        if (repo / rel).exists():
            git(repo, "add", "--", rel)

    staged = [l for l in git(repo, "diff", "--cached", "--name-only").splitlines() if l.strip()]
    junk = [f for f in staged if any(h in f for h in JUNK_HINT)]

    print(f"\n已暂存 {len(staged)} 个文件")
    if copied_runtime:
        print(f"已更新运行时数据 {len(copied_runtime)} 个"
              + (f"（旧文件备份到 {a.backup_dir}）" if a.backup_dir else ""))
    if junk:
        print(f"\n⚠ 暂存区里有垃圾文件，提交前必须 git restore --staged 掉：")
        for f in junk[:20]:
            print(f"    {f}")
        return 1

    print("暂存区干净（无 pyc/.DS_Store/.venv 混入）。")
    print("\n下一步：核对 `git diff --cached --stat`，然后按本仓库 main 的提交约定提交。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
