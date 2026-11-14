#!/usr/bin/env python3
"""升级后的验证：残留冲突标记、语法、占位符回归、config 键对账、真实 import。

"合并完成"和"框架能跑"是两件事。语法过了不代表 import 得动，import 得动也不代表
你的自定义因子还认得新版 core 的接口。所以按五层递进检查，越往后越接近真实运行：

1. 冲突标记 —— 漏掉一个 `<<<<<<<` 就是语法错误，先扫一遍最便宜
2. 语法解析 —— 覆盖全仓 .py，包括没冲突但被误编辑的文件
3. 占位符回归 —— 官方包带 /Users/xxxx 这类占位路径，被合进来等于本地配置被打回官方默认
4. config 键对账 —— 官方 config.py 有、本地没有的键；缺键不报错，只会静默改道
5. 真实 import —— 用项目自己的 venv，逐个 import core 与你的自定义目录

第 4 步必须是全集对账，而不是只看"本次新增了哪些键"。真实事故：官方在 v2.3.0 加了
use_intraday_cache，本地那次没接住，此后 5 次升级都只比对当次 delta，
于是这个键永远进不了视野 —— 直到某天走到那条分支才崩。差集要对官方分支的完整键集取。

第 3 步只扫"这次合并真正改动过的文件"。整仓扫会被官方示例配置淹没：
examples/、tools_official/、configlib/官方策略/ 里本来就写满占位符，那是官方样例的正常长相，
报出来只会让你对告警脱敏，反而漏掉 config.py 里真正的回归。

用法:
    python3 verify.py [--repo PATH] [--since REF] [--official-ref REF]
                      [--python PATH] [--no-import] [--custom-dirs ...]
                      [--allow-missing-dependency NAME ...]

第 4 步也可以在升级**之前**单独跑一次，用来体检历史欠账（往届升级漏掉的键）。
"""

import argparse
import ast
import os
import re
import subprocess
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_support import effective_keys, mode_exclusions, import_skips, run_probe

NOISE = {".git", "__pycache__", ".venv", "venv", ".idea", ".vscode", ".pytest_cache",
         ".ruff_cache", ".mypy_cache", "node_modules", ".ipynb_checkpoints"}
# 真正的冲突标记是"恰好 7 个符号 + 空格或行尾"。必须卡这个边界，否则会误报：
# 业务代码里常有 `>>>>>>>>>>>> 2qgm <<<<<<<<<<<<` 这类装饰性分隔线（十几个尖括号），
# 宽松的 `>{7}` 会把它当成残留冲突，而这种假警报比漏报更伤 —— 它会让你不再信任这项检查。
MARKERS = re.compile(r"^(?:(?:<{7}|>{7})(?=[ \t]|$)|={7}$)", re.M)
TEXTLIKE = {".py", ".md", ".html", ".txt", ".json", ".toml", ".yaml", ".yml", ".ipynb", ".cfg"}

# 官方包里的占位符特征。合并后"本该是你自己配置"的文件里再出现这些，说明配置被打回官方默认了。
PLACEHOLDERS = [
    (r"/Users/xxx+", "官方占位用户目录"),
    (r"\*{3,}[^*\n]*填写[^*\n]*\*{3,}", "官方占位提示串"),
    (r"[/\\]path[/\\]to[/\\]", "官方占位路径"),
    (r"your[-_]?api[-_]?key", "占位 API key"),
]

# 官方样例目录：这些地方出现占位符是正常的，不算回归。
SAMPLE_HINTS = ("examples/", "example/", "tools_official/", "官方策略", "样例", "sample")

# 代码读取 config 的几种写法。缺键之所以危险，是因为这些写法都不会报错，只会悄悄换一条路。
# 尤其注意 hasattr 那种：它的兜底往往落在**另一个名字**的遗留键上，
# 光扫 "getattr 的默认值" 是扫不出来的（真实事故里就是这样漏掉的）。
CONFIG_READS = [
    (re.compile(r"""getattr\(\s*config\s*,\s*["'](\w+)["']\s*,\s*([^,)]+)\s*\)"""), "getattr"),
    (re.compile(r"""config_dict\.get\(\s*["'](\w+)["']\s*,\s*([^,)]+)\s*\)"""), "get"),
    (re.compile(r"""hasattr\(\s*config\s*,\s*["'](\w+)["']\s*\)"""), "hasattr"),
]

# 你自己的内容目录 —— 它们能否 import 成功，才是"新版 core 没破坏我的东西"的真正判据。
# 注意不含 examples/：官方示例配置 import 时会自己 sys.exit 或触发运行逻辑，不适合当探针。
DEFAULT_CUSTOM = ["configlib", "factors", "signals", "sections", "strategy", "positions", "capital_flows"]


def config_assignments(src_text):
    """config.py 里的模块级赋值：名字 -> (首次赋值的字面量值, 是否多处赋值)。

    按行号取"首次"，因为 config.py 常有同名二次赋值（例如末尾 try/except 里把
    report_version 回落成 'v1'）—— 拿最后一次会得出"官方值=v1"这种错误结论。
    非字面量（表达式、函数调用）无法和 fallback 比较，值记为 None 并标记未知。

    还要区分**模块顶层赋值**和**条件分支内赋值**：只有顶层的才保证执行。
    实测踩过：本地 config.py 里 performance_mode 只在客户端配置块(if ...)里赋值，
    普通回测时那段不执行，运行时 hasattr(config, "performance_mode") 就是 False ——
    只按"名字出现过"判定会把它误判成"本地有这个键"。
    """
    try:
        tree = ast.parse(src_text)
    except SyntaxError:
        return {}
    toplevel = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            toplevel.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            toplevel.add(node.target.id)

    def module_nodes(node):
        # 条件/try 中的赋值属于模块作用域；函数、类和 lambda 内的赋值不是配置键。
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return
        yield node
        for child in ast.iter_child_nodes(node):
            yield from module_nodes(child)

    found = []
    for node in module_nodes(tree):
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
        else:
            continue
        try:
            val, known = ast.literal_eval(node.value), True
        except (ValueError, SyntaxError, TypeError):
            val, known = None, False
        for n in names:
            found.append((node.lineno, n, val, known))
    found.sort(key=lambda x: x[0])
    out = {}
    for _, name, val, known in found:
        if name in out:
            out[name] = (out[name][0], out[name][1], True, name in toplevel)  # 多处赋值
        else:
            out[name] = (val, known, False, name in toplevel)
    return out


def scan_config_reads(repo, dirs=("core", "extend")):
    """扫代码里所有 config 读取点：key -> [(kind, fallback原文, 位置), ...]"""
    reads = {}
    for d in dirs:
        base = repo / d
        if not base.is_dir():
            continue
        for p in base.rglob("*.py"):
            if any(part in NOISE for part in p.parts):
                continue
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for rx, kind in CONFIG_READS:
                for m in rx.finditer(txt):
                    key = m.group(1)
                    raw = m.group(2).strip() if kind != "hasattr" else None
                    loc = f"{p.relative_to(repo)}:{txt[: m.start()].count(chr(10)) + 1}"
                    reads.setdefault(key, []).append((kind, raw, loc))
    return reads


def git(repo, *args, check=False):
    r = subprocess.run(["git", "-C", str(repo), "-c", "core.quotePath=false", *args],
                       capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"git {' '.join(args)} 失败")
    return r.stdout


def walk_py(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in NOISE]
        for fn in filenames:
            if fn.endswith(".py"):
                yield Path(dirpath) / fn


def find_python(repo):
    for c in (repo / ".venv/bin/python", repo / ".venv/Scripts/python.exe"):
        if c.exists():
            return str(c)
    return sys.executable


def merge_changed_files(repo, since):
    """基准到当前工作树的变化：含暂存、未暂存和未忽略的新增文件。"""
    if since:
        base = since
    elif git(repo, "rev-parse", "--verify", "--quiet", "MERGE_HEAD").strip():
        base = "HEAD"                       # 合并未提交：dev 的升级前状态
    else:
        parents = git(repo, "rev-list", "--parents", "-n", "1", "HEAD").split()
        if len(parents) >= 3:
            base = parents[1]               # 已提交：dev 侧第一父
        else:
            return None
    changed = git(repo, "diff", "--name-only", "-z", base, "--", check=True)
    untracked = git(repo, "ls-files", "--others", "--exclude-standard", "-z", check=True)
    return sorted({p for p in (changed + untracked).split("\0") if p})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--since", help="占位符扫描的对比基准 ref（默认自动取合并提交的第一父）")
    ap.add_argument("--official-ref",
                    help="官方分支/ref（默认自动探测 main、master）；用于 config 键对账")
    ap.add_argument("--no-import", action="store_true")
    ap.add_argument("--python", help="实际运行时解释器路径；默认优先项目 .venv，语法与 import 使用同一解释器")
    ap.add_argument("--custom-dirs", nargs="*", default=None)
    ap.add_argument("--allow-missing-dependency", nargs="*", default=[], metavar="NAME",
                    help="仅放行已在升级前确认缺失且不影响当前运行的可选依赖（顶层包名）")
    ap.add_argument("--effective-config", action="store_true",
                    help="在隔离副本中加载config，核对动态生效的属性名（不输出配置值）")
    ap.add_argument("--config-layout", choices=("flat", "selection-position"), default="flat",
                    help="默认保持普通框架键全集；仅显式选择时识别选币/仓管互斥字段")
    ap.add_argument("--import-policy", help="审阅过的逐文件跳过清单，必须含path/sha256/reason")
    a = ap.parse_args()
    if a.no_import and a.effective_config:
        ap.error("--no-import不能与--effective-config同时使用：后者会执行配置代码")
    if a.config_layout != "flat" and not a.effective_config:
        ap.error("selection-position布局需要--effective-config核验真实模式")

    repo = Path(git(Path(a.repo), "rev-parse", "--show-toplevel").strip() or a.repo)
    py = str(Path(a.python or find_python(repo)).expanduser().absolute())
    if not Path(py).is_file():
        ap.error(f"解释器不存在: {py}")
    if os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(py):
        # AST 语法/配置解析也必须使用运行时版本，不能只把 import 切到 venv。
        return subprocess.run([py, str(Path(__file__).resolve()), *sys.argv[1:], "--python", py]).returncode
    problems, warns = 0, 0
    try:
        skips = import_skips(repo, a.import_policy)
    except (ValueError, KeyError, OSError) as error:
        ap.error(str(error))

    # ---- 1. 冲突标记 ----
    hits = []
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in NOISE]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() not in TEXTLIKE:
                continue
            try:
                if MARKERS.search(p.read_text(encoding="utf-8", errors="ignore")):
                    hits.append(str(p.relative_to(repo)))
            except OSError:
                pass
    print(f"[1/5] 冲突标记: {'残留 ' + str(len(hits)) + ' 个文件' if hits else '干净'}")
    for h in hits:
        print(f"        <<< {h}")
    problems += len(hits)

    # ---- 2. 语法 ----
    # 屏蔽 SyntaxWarning：被扫的业务代码里有历史遗留的无效转义（如 "\ "），
    # 那是既有状况不是本次升级引入的，混在输出里只会盖住真正的 SyntaxError。
    bad, total = [], 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        for p in walk_py(repo):
            total += 1
            try:
                ast.parse(p.read_text(encoding="utf-8", errors="ignore"))
            except SyntaxError as e:
                bad.append(f"{p.relative_to(repo)}:{e.lineno} {e.msg}")
    print(f"[2/5] 语法解析: {total} 个 .py, {'失败 ' + str(len(bad)) if bad else '全部通过'}")
    for b in bad:
        print(f"        ✗ {b}")
    problems += len(bad)

    # ---- 3. 占位符回归（只看本次改动过的文件，且跳过官方样例目录）----
    try:
        changed = merge_changed_files(repo, a.since)
    except RuntimeError as e:
        ap.error(str(e))
    scope = changed if changed is not None else [
        str(p.relative_to(repo)) for p in walk_py(repo)]
    scope = [f for f in scope if not any(h in f for h in SAMPLE_HINTS)]
    ph = []
    for rel in scope:
        p = repo / rel
        if not p.is_file() or p.suffix.lower() not in TEXTLIKE:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pat, label in PLACEHOLDERS:
            for m in re.finditer(pat, txt, re.I):
                ph.append(f"{rel}:{txt[: m.start()].count(chr(10)) + 1} [{label}] {m.group(0)[:60]}")
    src = f"本次改动的 {len(scope)} 个文件" if changed is not None else f"全仓 {len(scope)} 个文件(非合并提交)"
    print(f"[3/5] 占位符回归 ({src}): {'发现 ' + str(len(ph)) + ' 处' if ph else '未发现'}")
    for x in ph[:25]:
        print(f"        ! {x}")
    if ph:
        print("        ^ 逐个确认：本地真实配置是否被官方默认值覆盖了")
    problems += len(ph)

    # ---- 4. config 键全集对账 ----
    # 官方 config.py 有、本地没有的键。这类缺失不会报错、不留冲突标记、语法和 import 全过，
    # 只是代码里的 fallback 悄悄接管，把执行路径导去另一侧。必须对**全集**取差，
    # 只看"本次新增的键"会让往届漏掉的键永远隐身。
    off_ref = a.official_ref
    if not off_ref:
        for cand in ("main", "master"):
            if git(repo, "rev-parse", "--verify", "--quiet", cand).strip():
                off_ref = cand
                break
    off_src = git(repo, "show", f"{off_ref}:config.py") if off_ref else ""
    local_cfg = repo / "config.py"
    if not off_src or not local_cfg.is_file():
        why = "未识别官方分支" if not off_src else "本地无 config.py"
        print(f"[4/5] config 键对账: 跳过（{why}）")
    else:
        off = config_assignments(off_src)
        loc = config_assignments(local_cfg.read_text(encoding="utf-8", errors="ignore"))
        excluded = set()
        if a.effective_config:
            try:
                live = effective_keys(repo, py)
                if a.config_layout == "selection-position":
                    excluded = mode_exclusions(live['keys'], live['selection'], live['position'])
                loc = {key: (None, False, False, True) for key in live['keys']}
                print(f"        动态配置：隔离副本加载成功；互斥字段排除 {sorted(excluded)}")
            except (ValueError, RuntimeError) as error:
                print(f"        ✗ 有效配置校验失败: {error}")
                problems += 1
        missing = sorted(set(off) - set(loc) - excluded)
        reads = scan_config_reads(repo)
        hard, soft = [], []
        for k in missing:
            val, known, multi, _ = off[k]
            rs = reads.get(k, [])
            kinds = {kind for kind, _, _ in rs}
            if not rs:
                hard.append(f"{k}: 官方={val!r}；未见静态读取点仍可能被动态消费，不能放行缺键")
                continue
            if "hasattr" in kinds:
                loc_s = next(l for kind, _, l in rs if kind == "hasattr")
                hard.append(f"{k}: 官方={val!r}，代码用 hasattr 判定 [{loc_s}] —— "
                            f"兜底可能落在另一个名字的遗留键上，必须人工看这段分支")
                continue
            fbs = []
            for kind, raw, _ in rs:
                try:
                    fbs.append(ast.literal_eval(raw))
                except (ValueError, SyntaxError, TypeError):
                    fbs.append(f"<非字面量:{raw}>")
            loc_s = rs[0][2]
            if multi or not known:
                hard.append(f"{k}: 官方值多处赋值/非字面量，fallback={fbs!r} [{loc_s}]，不能放行缺键")
            elif any(val != f for f in fbs):
                hard.append(f"{k}: 官方={val!r} 但 fallback={fbs!r} [{loc_s}] —— 行为已偏离官方")
            else:
                hard.append(f"{k}: 官方={val!r}，fallback 同值 [{loc_s}] —— "
                            f"当前无差异，但官方改值时本地不会跟随")
        # 官方顶层有、本地只在条件分支里赋值 —— 普通运行时该属性可能根本不存在
        for k in sorted(set(off) & set(loc)):
            if off[k][3] and not loc[k][3]:
                soft.append(f"{k}: 官方在模块顶层赋值，本地只在条件分支内赋值 —— "
                            f"该分支不执行时运行时属性缺失，等同缺键，确认是否有意为之")

        n = len(missing)
        print(f"[4/5] config 键对账 (官方 {off_ref}): "
              f"{'官方 ' + str(n) + ' 个键本地缺失' if n else '键集一致'}")
        for h in hard:
            print(f"        ✗ {h}")
        for s in soft:
            print(f"        ⚠ {s}")
        if hard:
            print("        ^ 核对有效配置来源及互斥模式；动态配置请用--effective-config，勿机械补齐另一模式字段")
        problems += len(hard)
        warns += len(soft)

    # ---- 5. 真实 import ----
    if a.no_import:
        print("[5/5] import: 已跳过")
    else:
        custom = a.custom_dirs if a.custom_dirs is not None else [
            d for d in DEFAULT_CUSTOM if (repo / d).is_dir()]
        # 顶层名用于区分"缺第三方依赖"和"框架真的坏了"
        local_tops = {p.name.removesuffix(".py") for p in repo.iterdir()
                      if p.name not in NOISE and (p.is_dir() or p.suffix == ".py")}
        code = f'''
import importlib, pathlib, sys, json
repo = pathlib.Path.cwd()
out = {{"core_ok": 0, "core_fail": [], "custom": [], "skipped": []}}
skips = {skips!r}

def imp(mod):
    try:
        importlib.import_module(mod); return None
    except BaseException as e:
        return f"{{type(e).__name__}}: {{e}}"

if (repo / "config.py").exists():
    e = imp("config")
    if e: out["core_fail"].append(["config", e])
    else: out["core_ok"] += 1

for p in sorted((repo / "core").rglob("*.py")) if (repo / "core").is_dir() else []:
    if "__pycache__" in p.parts: continue
    parts = list(p.relative_to(repo).with_suffix("").parts)
    if parts[-1] == "__init__": parts = parts[:-1]
    if not parts: continue
    mod = ".".join(parts)
    e = imp(mod)
    if e: out["core_fail"].append([mod, e])
    else: out["core_ok"] += 1

for d in {custom!r}:
    base = repo / d
    if not base.is_dir(): continue
    ok, fails = 0, []
    for p in sorted(base.rglob("*.py")):
        if any(part in {NOISE!r} for part in p.relative_to(base).parts): continue
        if p.name == "__init__.py": continue
        relative = p.relative_to(repo).as_posix()
        if relative in skips:
            entry = skips[relative]
            if not entry.get("loader"):
                out["skipped"].append([relative, entry["reason"]])
                continue
            try:
                module, function = entry["loader"].split(":")
                value = getattr(importlib.import_module(module), function)(relative)
                if not isinstance(value, dict) or not value:
                    raise ValueError("profile loader must return a nonempty configuration dictionary")
            except BaseException as error:
                fails.append([str(p.relative_to(base)), f"{{type(error).__name__}}: {{error}}"])
            else:
                ok += 1
            continue
        if any(part in ("examples", "example") for part in p.relative_to(base).parts):
            out["skipped"].append([relative, "样例/辅助脚本仅做静态检查，不作为模块import探针"])
            continue
        e = imp(".".join(p.relative_to(repo).with_suffix("").parts))
        if e: fails.append([str(p.relative_to(base)), e])
        else: ok += 1
    out["custom"].append([d, ok, fails])
print("@@JSON@@" + json.dumps(out, ensure_ascii=False))
'''
        print(f"[5/5] import (venv: {py}; 隔离副本)")
        try:
            d = run_probe(repo, py, code)
        except RuntimeError as error:
            print(f"        ✗ {error}")
            problems += 1
        else:
            for path, reason in d['skipped']:
                print(f"        ⚠ 已登记跳过 {path}: {reason}")
            warns += len(d['skipped'])

            def classify(err):
                """缺第三方依赖单列展示，但不能自动假定它是既有可选依赖。"""
                m = re.search(r"No module named '([^']+)'", err)
                if m and m.group(1).split(".")[0] not in local_tops:
                    return "dep", m.group(1).split(".")[0]
                return "fail", None

            hard, dep = [], {}
            for mod, err in d["core_fail"]:
                k, name = classify(err)
                (dep.setdefault(name, []).append(f"core:{mod}") if k == "dep"
                 else hard.append(f"{mod}: {err}"))
            print(f"        core: {d['core_ok']} ok, {len(hard)} 真失败, "
                  f"{sum(len(v) for v in dep.values())} 缺依赖")
            for h in hard[:15]:
                print(f"        ✗ {h}")
            problems += len(hard)

            for name, ok, fails in d["custom"]:
                hf = []
                for fn, err in fails:
                    k, dn = classify(err)
                    (dep.setdefault(dn, []).append(f"{name}/{fn}") if k == "dep"
                     else hf.append(f"{fn}: {err}"))
                flag = "" if not hf else f", {len(hf)} 真失败"
                print(f"        {name}: {ok} ok{flag}")
                for h in hf[:8]:
                    print(f"        ✗ {name}/{h}")
                problems += len(hf)

            for name, users in sorted(dep.items()):
                allowed = name in a.allow_missing_dependency
                print(f"        {'⚠' if allowed else '✗'} 缺第三方依赖 '{name}' —— 影响 {len(users)} 个模块 "
                      f"(如 {users[0]})；{'已明确放行的既有可选依赖' if allowed else '未放行，验证失败'}")
                if allowed:
                    warns += len(users)
                else:
                    problems += len(users)

    print()
    if problems:
        verdict = f"{problems} 处问题待处理"
    else:
        verdict = "静态检查通过（未运行 import）" if a.no_import else "检查通过"
    if warns:
        verdict += f"（另有 {warns} 处告警：已登记跳过 / 样例静态检查 / 可选依赖 / 条件配置，需逐条复核）"
    print(f"结论: {verdict}")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
