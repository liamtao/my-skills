#!/usr/bin/env python3
"""侦察官方新版框架包，并算出升级会带来的文件增删。

全程只读 —— 不碰 git 状态，不动任何文件。目的是让你在动手之前就掌握全貌：
官方包在哪、版本是多少、main 上哪些文件会被删、哪些是官方新增、
运行时数据目录有什么变化、这个仓库的分支名和提交约定长什么样。

用法:
    python3 scout.py [--repo PATH] [--downloads PATH] [--hours 24] [--json]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from file_inventory import package_inventory

# 这些目录/文件从"代码文件清单"里排除：它们是构建产物或编辑器状态，
# 不属于官方框架的代码内容，混进来只会让增删清单产生噪音。
NOISE = {".git", "__pycache__", ".DS_Store", ".venv", "venv", ".idea", ".vscode",
         ".pytest_cache", ".ruff_cache", ".mypy_cache", "node_modules", ".ipynb_checkpoints"}

VERSION_SUFFIX = re.compile(r"[-_]v?(\d+(?:\.\d+)*(?:[a-zA-Z]\w*)?)$")


def run(args, cwd=None, check=True):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"命令失败 {' '.join(args)}\n{r.stderr}")
    return r.stdout


def git(repo, *args, check=True):
    # core.quotePath=false 很关键：默认 git 会把中文路径转义成 "\346\214..."，
    # 导致中文文件名在清单比对里被误判成"只存在于一边"。
    return run(["git", "-C", str(repo), "-c", "core.quotePath=false", *args], check=check)


def norm(name):
    """把仓库名/包名归一化后再比对 —— 官方包用连字符，本地目录可能用下划线。

    例: select_stock_pro / select-stock-pro / SelectStockPro 都归一到 selectstockpro
    """
    return re.sub(r"[^a-z0-9]", "", name.lower())


def strip_version(dirname):
    """从官方包目录名剥离版本后缀，返回 (基础名, 版本或 None)。

    select-coin-pro_v2.1.0 -> (select-coin-pro, 2.1.0)
    stock-fusion-v3.0.0    -> (stock-fusion, 3.0.0)
    """
    m = VERSION_SUFFIX.search(dirname)
    if m:
        return dirname[: m.start()], m.group(1)
    return dirname, None


def walk_files(root, ignored_tops):
    """收集代码文件相对路径。运行时数据目录单独归类，不混进代码清单。"""
    code, runtime = set(), set()
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in NOISE]
        rel_dir = Path(dirpath).relative_to(root)
        top = rel_dir.parts[0] if rel_dir.parts else ""
        for fn in filenames:
            if fn in NOISE:
                continue
            rel = str(rel_dir / fn) if rel_dir.parts else fn
            (runtime if top and top in ignored_tops else code).add(rel)
    return code, runtime


def runtime_top_dirs(repo, pkg):
    """找出官方包里那些"被 git 忽略"的顶层目录 —— 它们装的是运行时数据。

    这类目录（通常是 data/ logs/）不进 git，所以 `git diff` 完全看不见，
    但官方包里可能带着必须更新的运行时文件（最小下单量表、币种列表等），直接影响能否跑起来。
    它们要单独决策，不能跟代码一起无脑覆盖。

    判定交给 `git check-ignore` 而不是自己解析 .gitignore：很多仓库用的是完整的
    Python 模板 gitignore（上百条，含 docs/ lib/ build/ private/ 等），自己解析会把
    这些全当成运行时目录，一旦官方包真带了 docs/ 就会被静默跳过、代码丢失。
    而且只检查"官方包里真实存在的顶层目录"，范围最小化。
    """
    tops = [p.name for p in Path(pkg).iterdir() if p.is_dir() and p.name not in NOISE]
    if not tops:
        return set()
    r = subprocess.run(["git", "-C", str(repo), "check-ignore", "--", *[t + "/" for t in tops]],
                       capture_output=True, text=True)
    return {line.strip().rstrip("/") for line in r.stdout.splitlines() if line.strip()}


def detect_branches(repo):
    branches = [b.strip().lstrip("* ").split()[0]
                for b in git(repo, "branch", "--format=%(refname:short)").splitlines() if b.strip()]
    current = git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    official = next((b for b in ("main", "master") if b in branches), None)
    # 本地修改分支：优先当前分支（若不是官方分支），否则挑 dev*
    if current and current != official:
        local = current
    else:
        cands = [b for b in branches if b != official]
        local = cands[0] if len(cands) == 1 else None
    return {"all": branches, "current": current, "official_branch": official,
            "local_branch": local,
            "local_candidates": [b for b in branches if b != official]}


def package_version(pkg):
    """从包内容里读版本，用来交叉验证目录名上的版本号是否可信。"""
    for rel in ("core/version.py", "version.py", "core/utils/version.py"):
        p = Path(pkg) / rel
        if p.exists():
            m = re.search(r"sys_version\s*=\s*['\"]([^'\"]+)['\"]", p.read_text(encoding="utf-8", errors="ignore"))
            if m:
                return m.group(1), rel
    for note in ("更新说明.md", "README.md"):
        p = Path(pkg) / note
        if p.exists():
            m = re.search(r"^#+\s*v?(\d+(?:\.\d+)+)", p.read_text(encoding="utf-8", errors="ignore"), re.M)
            if m:
                return m.group(1), note
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--downloads", default=str(Path.home() / "Downloads"))
    ap.add_argument("--hours", type=float, default=24.0,
                    help="优先窗口（小时）。窗口外的候选依然会列出，但会被标记")
    ap.add_argument("--package", help="直接指定官方包路径，跳过自动查找")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    repo = Path(run(["git", "-C", a.repo, "rev-parse", "--show-toplevel"]).strip())
    repo_name = repo.name
    br = detect_branches(repo)
    if not br["official_branch"]:
        print("错误：找不到 main/master 分支，这个仓库可能不是 main 追官方 / dev 放修改的结构。", file=sys.stderr)
        return 2

    out = {"repo": str(repo), "repo_name": repo_name, "branches": br}
    if (repo / "pyproject.toml").is_file() and (repo / "uv.lock").is_file():
        out["dependency_workflow"] = {"kind": "uv-lock", "file": "pyproject.toml"}
    else:
        requirements = next((name for name in ("requirements-local.txt", "requirements.txt")
                             if (repo / name).is_file()), None)
        out["dependency_workflow"] = {"kind": "requirements" if requirements else "manual", "file": requirements}

    # ---- 定位官方包 ----
    if a.package:
        chosen = Path(a.package).expanduser().resolve()
        cands = [{"path": str(chosen), "version": strip_version(chosen.name)[1], "age_hours": None,
                  "within_window": True}]
    else:
        cands = []
        dl = Path(a.downloads).expanduser()
        for d in (p for p in dl.iterdir() if p.is_dir()) if dl.exists() else []:
            base, ver = strip_version(d.name)
            if norm(base) != norm(repo_name):
                continue
            age = (time.time() - d.stat().st_mtime) / 3600
            cands.append({"path": str(d), "version": ver, "age_hours": round(age, 1),
                          "within_window": age <= a.hours})
        # 先按"在窗口内"排，再按版本号排，最后按新鲜度 —— 这样正常情况下第一个就是想要的
        def vkey(c):
            return tuple(int(x) for x in re.findall(r"\d+", c["version"] or "0"))
        cands.sort(key=lambda c: (c["within_window"], vkey(c), -(c["age_hours"] or 0)), reverse=True)
        chosen = Path(cands[0]["path"]) if cands else None

    out["candidates"] = cands
    if not chosen:
        out["error"] = (f"在 {a.downloads} 里找不到与仓库名 '{repo_name}' 匹配的官方包。"
                        "确认已下载解压，或用 --package 手动指定。")
        print(json.dumps(out, ensure_ascii=False, indent=2) if a.json else out["error"])
        return 1

    out["package"] = str(chosen)
    pv, pv_src = package_version(chosen)
    out["package_version_in_code"] = pv
    out["package_version_source"] = pv_src
    out["dir_version"] = strip_version(chosen.name)[1]

    # ---- 比对文件清单 ----
    ign = runtime_top_dirs(repo, chosen)
    out["gitignored_top_dirs"] = sorted(ign)
    code_files, runtime_files = package_inventory(repo, chosen)
    off_code, off_runtime = set(code_files), set(runtime_files)
    main_files = {l for l in git(repo, "ls-tree", "-r", "--name-only",
                                 br["official_branch"]).splitlines() if l.strip()}

    only_main = sorted(main_files - off_code)
    only_off = sorted(off_code - main_files)
    out["only_in_main"] = only_main
    out["only_in_official"] = only_off

    # 把 only_in_main 分成两类，省掉大部分本来要问用户的判断：
    #   官方旧版包里也没有  -> 从来不是官方的（本地往 main 上加的东西），保留即可
    #   官方旧版包里有      -> 官方这次停止分发了，删除是不可逆的，需要问用户
    prev = next((c for c in cands if c["path"] != str(chosen) and c["version"]), None)
    out["prev_package"] = prev["path"] if prev else None
    if prev and only_main:
        prev_code, _ = walk_files(prev["path"], ign)
        out["never_official"] = sorted(f for f in only_main if f not in prev_code)
        out["official_dropped"] = sorted(f for f in only_main if f in prev_code)
    else:
        out["never_official"], out["official_dropped"] = [], []
    out["common_count"] = len(main_files & off_code)
    out["official_runtime_files"] = sorted(off_runtime)

    # main 当前版本，用于写提交信息
    cur = None
    for rel in ("core/version.py", "version.py"):
        c = git(repo, "show", f"{br['official_branch']}:{rel}", check=False)
        m = re.search(r"sys_version\s*=\s*['\"]([^'\"]+)['\"]", c)
        if m:
            cur = m.group(1)
            break
    out["current_main_version"] = cur
    out["main_recent_commits"] = [l for l in git(repo, "log", "--oneline", "-6",
                                                 br["official_branch"]).splitlines()]
    out["dirty_files"] = [l for l in git(repo, "status", "--porcelain").splitlines() if l.strip()]

    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    p = print
    p(f"仓库          {repo}")
    p(f"依赖同步      {out['dependency_workflow']}")
    p(f"官方分支      {br['official_branch']}   本地修改分支  {br['local_branch'] or '?? 需要确认'}")
    if not br["local_branch"]:
        p(f"  候选分支: {br['local_candidates']}  ← 有多个，必须先确认用哪个")
    p(f"当前 main 版本 {cur or '未知'}  ->  官方包版本 {pv or out['dir_version'] or '未知'}"
      + (f" (读自 {pv_src})" if pv_src else ""))
    p(f"官方包        {chosen}")
    if len(cands) > 1:
        p("  其他候选:")
        for c in cands[1:]:
            p(f"    {Path(c['path']).name}  版本={c['version']}  {c['age_hours']}小时前"
              + ("" if c["within_window"] else "  [窗口外]"))
    if cands and not cands[0]["within_window"]:
        p(f"  ⚠ 选中的包是 {cands[0]['age_hours']} 小时前的，超出 {a.hours} 小时窗口 —— 确认这是最新版")
    p("")
    p(f"main 提交约定 (照抄这个格式):")
    for c in out["main_recent_commits"][:4]:
        p(f"    {c}")
    p("")
    p(f"文件比对：共有 {out['common_count']}  官方新增 {len(only_off)}  main 独有 {len(only_main)}")
    if only_off:
        p("  官方新增（会加进来）:")
        for f in only_off[:40]:
            p(f"    + {f}")
        if len(only_off) > 40:
            p(f"    ... 还有 {len(only_off) - 40} 个")
    if only_main:
        if out["never_official"] or out["official_dropped"]:
            p(f"  main 独有 —— 已用旧版官方包 {Path(out['prev_package']).name} 做初步分类"
              f"（只比对了这一个旧版，是强信号但非定论）:")
            if out["never_official"]:
                p(f"    · 旧版官方包里也没有 → 大概率是本地加到 main 上的，倾向保留，"
                  f"共 {len(out['never_official'])} 个:")
                for f in out["never_official"][:12]:
                    p(f"        = {f}")
                if len(out["never_official"]) > 12:
                    p(f"        ... 还有 {len(out['never_official']) - 12} 个")
            if out["official_dropped"]:
                p(f"    · ⚠ 官方本次停止分发（删除不可逆，需要问用户）共 {len(out['official_dropped'])} 个:")
                for f in out["official_dropped"]:
                    p(f"        - {f}")
        else:
            p("  ⚠ main 独有（下载目录里没有旧版官方包可比对，需逐个判断）:")
            for f in only_main:
                p(f"    - {f}")
    if out["official_runtime_files"]:
        p(f"  官方包内的运行时数据文件（未跟踪且被 gitignore 忽略，不进 git 但影响运行）:")
        for f in out["official_runtime_files"][:20]:
            p(f"    ~ {f}")
    if out["dirty_files"]:
        p("")
        p(f"  ⚠ 工作区有 {len(out['dirty_files'])} 处未提交改动 —— 升级前必须先处理干净")
    return 0


if __name__ == "__main__":
    sys.exit(main())
