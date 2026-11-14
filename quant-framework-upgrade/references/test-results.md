# 兼容性测试记录

验证日期：2026-11-14。修改范围仅共享 Skill，未执行真实框架升级或回测。

## 自动回归

运行 `python3 -B scripts/test_upgrade_tools.py`：27 项全部通过（包含原有 12 项），耗时约 12 秒。

覆盖：

- 原有官方分支替换、运行时数据备份前置及备份失败不写入、精确暂存、合并前后增量扫描、真实解释器选择、缺依赖显式放行。
- 动态有效配置发现、真实缺键仍失败；股票平铺配置保留全集校验；币圈互斥模式显式启用，混用或空值配置失败；no-import 不执行动态配置。
- 相对文件及 `__file__` 同目录写入只留在临时副本；网络连接拦截；新模块异常仍失败。
- 已审核档案精确指纹放行、指纹变更失败、core/config禁止排除、可运行profile走loader并保留新异常、嵌套辅助样例仅静态检查。
- 混合 data/ 中已跟踪参考文件更新暂存、未跟踪被忽略数据保留；dry-run无写入；新版.gitignore不阻止清单中的官方新代码暂存。
- requirements-local 与 uv.lock 工作流识别；迁移清单的指纹转换与修改后拒绝。

测试的分支切换和替换只发生在 TemporaryDirectory 里的玩具仓库。

## 当前币圈框架实际验证

使用目标项目 `.venv/bin/python`，在临时源码副本运行 `verify.py --since HEAD --effective-config --config-layout selection-position --import-policy <外部规则>`。

- 官方 26 个静态配置键中，24 个已动态生效，另 2 个属于未选仓管模式。有效键检查通过，没有补入互斥字段。
- 迁移规则从现有清单、禁用策略表及已审核基线 `b3b5b0d` 生成在仓库外；90 条逐文件规则，其中可运行profile经 loader 校验。
- core 含 config 31 项、configlib 46 项、factors 408 项、signals 6 项、sections 11 项、strategy 8 项、positions 10 项、capital_flows 2 项通过。
- 50 项明确未作为运行成功：30 个缺数据/缺依赖/ML配置、18 个已登记策略、2 个发帖辅助脚本。静态检查仍覆盖它们，不把这些项目称为可运行。
- 未执行框架升级、依赖安装、行情回测或真实数据更新。框架仍为 dev / b3b5b0d，Git 状态与验证前一致。

当前项目的静态扫描还覆盖本地保留的隔离回归副本，因此 Python 文件数高于工作源码数，不用扫描数量代替行为验证。临时副本机制不是恶意代码安全沙箱，不能隔离任意绝对路径写入或外部程序；在实盘框架中仍须先审查模块顶层行为。

## Skills Manager

通过 CLI 导出修改前备份，并保留既有 skill ID、preset 和部署范围。既有四个全局部署的 deploy dry-run 显示 changed_pairs=0；项目通过中央共享链接读取更新。不新增部署或重装技能。
