---
name: ben-a2b2-submit-pr
description: 在 Ben 的 A2B2 项目提交或更新 PR 时使用。根据实际 PR 范围为符合条件的本地分支命名，调用团队 a2b2-pre-push-checks 完成提交，再默认调用 a2b2-pr-to-linear 生成同步草稿，确认后写入 Linear。
---

# Ben 的 A2B2 PR 入口

用中文沟通。此技能只编排个人扩展；团队提交规则和 Linear 记录规则分别由下游技能维护。创建、编辑或部署此技能本身不启动提交流程。

## 1. 读取依赖并确定范围

- 以当前选定 checkout 的 Git 根目录为准，遵循该目录的 `AGENTS.md` 和本地 `AGENTS.override.md`。
- 在分支操作或提交准备前，读取该 checkout 的 `.agents/skills/a2b2-pre-push-checks/SKILL.md` 及其 `references/pull-request.md`。始终使用仓库当前版本，保持团队文件原样。
- 找到并读取已安装的 `a2b2-pr-to-linear`；优先使用项目 `.agents/skills/a2b2-pr-to-linear/SKILL.md`，也可通过 Skills Manager 解析中央库位置。后续按需读取它要求的依赖。缺失时明确报告，不自行复制或改写替代流程。
- 确认 Git 根目录、当前分支、工作区、worktree、远端、upstream 和已有 PR；保留其他任务的改动。按团队准备流程确定实际 PR base。涉及未合入的祖先层时，先复用已确认的 PR 策略；尚未确定则按团队流程询问，不能默认把祖先改动全算进本次 PR。
- 分析实际 base 到 head 的完整改动、提交历史和本次拟提交文件。范围确定后才命名；不以最近一次 commit 或分支旧名代替实际改动。

完成条件：本次 PR 的目标范围和 base 已确定，或阻塞与可继续的独立工作已说明。

## 2. 为尚未发布的普通主题分支命名

根据改动的主要用户结果生成简洁英文名称，沿用 `codex/<surface>-<type>-<topic>`；已有明确 ticket 时可用 `codex/<surface>-<type>-<ticket>-<topic>`。surface 如 `mobile`、`portal`、`marketing`、`repo`；type 如 `ui`、`ux`、`fix`。使用小写 kebab-case，省略日期和堆叠序号。当前名称已经准确表达该结果时保留。

若存在本次获准提交的改动，先按团队准备流程完成该提交，再在首次推送前检查以下条件。只有全部成立才自动本地改名：

- 当前是 Ben 的普通主题分支，工作区干净，无进行中的 Git 操作；不是 `main`、`sit`、`prod` 或其他 release／他人分支。
- 最新远端及 GitHub 查询证明旧分支未发布：没有 upstream、同名远端分支或已有 PR（含关闭和合并的 PR）。查询失败或证据不完整时保留原名。
- 没有其他分支通过本地 stack 元数据或 PR base 依赖它，也没有尚未确认的叠加关系。检查 `branch.*.a2b2-stack-parent` 等现有记录；存在依赖时保留原名。
- `git check-ref-format --branch` 验证通过，新名称在本地及相关远端均无冲突。

改名前报告旧名、新名及对应改动，随后执行已获准的 `git branch -m <new-name>`，不用 `-M`。核对 HEAD SHA、工作区和当前分支配置保持一致。自身已有 stack 元数据随本地分支配置保留；无法确认关系时跳过改名。

已推送、有 PR、存在依赖或其他条件不满足时，说明原因并沿用原名继续提交。改名不附带远端删除、远端改名、rebase 或 force-push；这些操作需要另行明确授权。更新同一 PR 时不反复改名，也不为改名自动 stash、丢弃文件或提交无关改动。

完成条件：已核验本地改名，或已说明保留原名的原因。

## 3. 按团队技能完成提交

继续执行 `a2b2-pre-push-checks` 和 PR preparation，在本次授权范围内完成所需门禁、提交、推送及 PR 创建或更新。门禁命令、截图、附件、模板及 draft／ready 规则以团队当前文件为准，不在个人入口复制或简化。

复用本次范围和修订仍适用的已完成步骤与授权。遇到检查失败或必需覆盖缺口，按团队规则停在对应阶段；不将失败描述成成功，也不进入 Linear 的交付写入。创建 PR 不授权合并或部署。

需要在浏览器中打开 GitHub、编辑 PR 或上传验收截图／录屏时，使用 ego-browser，并明确选择 Ego Lite 的 `Liam` profile。按当前 ego-browser 指南查询 profile ID 后创建对应 TaskSpace；现有 GitHub 连接器足够时继续优先使用连接器。

独立读回 PR，核对 URL、base、head SHA、范围及 draft／ready 状态。已有 PR 时更新或复用该 PR，避免重复创建。超时或结果不明确时先查询实际结果，再决定是否重试。

完成条件：已验证本次 PR 的实际结果，或已报告具体阻塞；区分本地验证、CI、合并和部署证据。

## 4. 默认进入 PR → Linear 草稿及确认

PR 成功创建或更新并读回后，自动调用 `a2b2-pr-to-linear`，传递已核验的 PR URL、实际 base/head SHA、验证结果和本次已明确的 Linear 选择。下游以该 PR 实际 diff 为准做覆盖分析、查重和 issue 草稿，不使用整个分支相对 main 的改动替代 stacked PR 范围。

- 默认走 issue 创建／更新，不同时调用 `linear-delivery-comment`。Ben 明确改为只发交付评论时，再遵循该技能的独立确认流程。
- 由 `a2b2-pr-to-linear` 处理 parent、assignee、实时 Sprint 选择、完整草稿、查重和读回规则；复用同批次已有选择。没有 Sprint 答案时继续保持待选择。
- **任何 Linear 写入前，必须先展示完整拟创建／更新批次并取得 Ben 对该具体批次的明确确认。** “提交 PR”、调用本入口或创建此技能均不算写入批准；等待期间可继续只读分析。已确认且范围未变的同一批次不重复索取批准。
- Ben 说先存草稿或不发时，保留草稿并报告位置，不写入。Ben 明确只提交 PR 或跳过 Linear 时尊重本次范围，不强制同步。
- 新 issue 的初始状态交由 `a2b2-pr-to-linear` 解析并在草稿中展示。变更现有 issue、父项或子项的状态需要 Ben 明确指定。
- 按下游规则记录每个成功写入的 issue 和 PR 关联；中断后从已核实结果继续。若 PR 修订或批次范围变化，检查差异并对实质新增或修改重新确认，避免重复建票。

完成条件：已交付等待确认的完整草稿，或批准后的每项写入均已读回验证。若 Linear 不可用，报告 PR 已完成及 Linear 待办，不重新提交 PR。

## 5. 汇报

简要列出分支名及是否改名、PR 链接、门禁与验收结果及缺口，以及 Linear 当前是待选择、待确认、已保存还是失败。已保存时给出 issue 链接；未保存时不声称同步完成。
