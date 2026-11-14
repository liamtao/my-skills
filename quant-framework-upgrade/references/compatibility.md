# 动态配置与历史档案验证

默认 `verify.py` 保留平铺静态配置的键全集检查，不依赖币圈目录或项目名。导入使用临时 Git 可见源码副本、真实运行时解释器与离线子进程；不是 OS 安全沙箱，绝对路径写入及外部命令仍需人工审查。不要把实盘启动器或有顶层交易动作的模块加入探针。

## 动态配置

```sh
python3 "<技能目录>/scripts/verify.py" --repo <仓库> --python <运行时Python> \
  --since <升级前本地tag> --effective-config
```

若该框架明确要求 `strategy_list` 与 `strategy_config/strategy_pool` 互斥，再增加 `--config-layout selection-position`。只忽略未选模式的字段；双模式、半个仓管配置、空策略及公共键缺失均失败。A 股和其他框架默认 `flat`，不会因同名字段被自动豁免。

`--no-import` 不执行配置，故不能核验动态字典，可能报告静态无法发现的键。不能靠关闭导入宣称动态配置已验证。

## 历史档案

`--import-policy` 接受经审阅的 JSON（实际文件须使用真实 SHA-256）：

```json
{"skip_imports": [
  {"path": "strategy/archive/Old.py", "sha256": "<已审核文件的64位SHA-256>", "reason": "原始依赖缺失，明确禁止启用"},
  {"path": "configlib/profile.py", "sha256": "<已审核文件的64位SHA-256>", "reason": "通过正式配置加载器校验", "loader": "configlib.loader:load_profile"}
]}
```

无 loader 的项目明确跳过 import 并列为未验证；带 loader 的项目调用 `load_profile(仓库相对文件路径)`，必须返回非空 dict，异常仍失败。只允许精确 Python 文件，指纹变化会在执行探针前失败；core 与根 config 不能排除。未知模块不自动跳过。嵌套 examples/ 下无正式profile规则的脚本仅做语法/冲突检查，不当作库模块执行。

已有迁移清单使用 `assets`（path、可选destination、destination_sha256）与 `profiles`（path、status、可选reason）时，可在升级前生成外部规则：

```sh
python3 "<技能目录>/scripts/migration_policy.py" --repo <仓库> \
  --manifest <仓库>/docs/migration-manifest.json \
  --blocked-strategies <仓库>/configlib/_blocked_strategies.json \
  --profile-loader configlib._profiles:load_profile \
  --baseline-ref <升级前本地tag> --output <仓库外的新文件.json>
```

这是显式选择的清单适配器，并非所有框架都需要这些文件。`validated_config` 交给 loader，`blocked/data_blocked/excluded_ml` 保留为已知跳过。资产已有目标指纹时必须吻合；生成的active配置若无资产记录，只能从指定的升级前Git引用取得指纹。脚本拒绝未知状态、缺失指纹和修改过的文件，输出文件不能在仓库里或覆盖旧策略。

生成后审阅规则，再将 `--import-policy <该文件>` 加到验证命令。升级后不要为了“变绿”重建指纹；改动过的档案需要重新审查。该清单不授予安装可选依赖、启用ML或实盘的权限。

## 参考数据与依赖

scout 和 apply 共用逐文件分类：已跟踪的官方参考文件保留在官方清单，即使位于被忽略目录也更新、暂存；仅未跟踪且被忽略的文件走 runtime-data 的 skip/copy/备份流程。不要全量暂存 data/，也不要把参考文件改成不受版本控制。

scout 的 `dependency_workflow` 区分 uv-lock、requirements 与 manual。仅报告建议，不执行安装。requirements-local 存在时保留其约束；同步使用明确的运行时解释器，不运行 uv lock/sync。依赖冲突和新缺依赖仍按 Skill 主流程处理。

## 测试

```sh
python3 -B "<技能目录>/scripts/test_upgrade_tools.py"
```

测试仅创建临时玩具仓库，验证替换/备份、动态与股票静态配置、互斥模式、真实缺键、精确档案策略、loader错误、离线及相对写入隔离、混合跟踪数据和两种依赖布局。不会升级真实量化项目。
