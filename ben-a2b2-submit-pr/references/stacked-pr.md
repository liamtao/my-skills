# 链式提交

调用示例：`$ben-a2b2-submit-pr 链式提交到当前分支`。

## 确定范围并逐层提交

1. 读取项目的 `a2b2-stacked-branches` 并按其检查流程确认依赖。目标默认为当前分支。列出从最新 `origin/main` 到目标的已证实祖先路径、每层 diff 和已有 PR。按团队规则跳过已落地或没有自身 diff 的层，排除目标上方和旁支。
2. 明确要求链式提交，已选择团队的「逐层提交 PR」策略，并授权连接这次范围内已核验的 Ben 自有 PR。若依赖不明确、既有 PR 需要改 base，或需要修改他人的分支，先给出具体分支、PR 和影响，等授权后再执行相关动作。推送、历史重写和合并继续按各自授权执行。
3. 按主流程从底到顶处理每层。底层目标为 `main`，其余层目标为最近尚未落地且有 PR 的父分支。每个新建或更新的 PR 都按本层实际 base 跑适用的团队门禁和 draft 规则。复用符合范围的已有 PR，只在本次有已授权的变更时更新。某层受阻时，保留已提交的层，停下依赖它的后续提交。

## 连接 GitHub stack

在所选层的 PR 均已读回后，核对仓库、编号、作者、open 状态、head SHA、base 和 draft/ready 状态。确认 PR 仍对应刚验证的修订与范围。每个依赖 PR 的 base 必须等于其父层的 head，最低 open 层指向 `main`。查询各 PR 的 stack 归属并读取相关 stack 的完整成员和顺序。已有历史合并层保留在 GitHub，只比较仍 open 的依赖链。按读回结果选择动作：

| GitHub 当前结果 | 动作 |
| --- | --- |
| 目标路径已按顺序连在同一 stack | 直接复用。目标以上的成员保持原状。 |
| 一个匹配的 stack 的 open 层恰好是目标路径的前几层，且未入栈的后续层可从当前栈顶连续追加 | 追加缺少的层。 |
| 所选 PR 均未入栈且至少有两层 | 按从底到顶的顺序创建 stack。 |
| 只有一层 open PR，且没有现成 stack | 汇报该 PR，后续有第二层时再建栈。 |
| 归属、顺序或 base 冲突，或查询失败后无法确认 | 保留现有 PR 和 stack，报告待处理原因。 |

创建或追加会涉及他人的 PR 时，先确认具体范围。向已有他人 PR 的 stack 追加 Ben 自有 PR 也属于这种情况。直接复用已匹配的 stack 只需读回。

通过能明确操作 stack 的 GitHub 工具执行。连接器缺少相应操作时，用带明确主机和仓库的 `gh api` 调用 [GitHub REST API](https://docs.github.com/en/rest/pulls/stacks?apiVersion=2026-03-10)：

- 查询归属用 `GET /repos/{owner}/{repo}/stacks?pull_request={number}`，读回顺序用 `GET /repos/{owner}/{repo}/stacks/{stack_number}`。
- 创建用 `POST /repos/{owner}/{repo}/stacks`，追加用 `POST /repos/{owner}/{repo}/stacks/{stack_number}/add`。请求体用 JSON `{"pull_requests":[101,102]}` 传整数编号。创建传全部有序编号，追加只传缺少的后缀。使用 `X-GitHub-Api-Version: 2026-03-10`。
- 连接只写 stack 成员关系。逐层推送和建 PR 由提交步骤负责。`gh stack submit` 和 `gh stack sync` 携带额外的推送操作，不用于这一步。

写入后独立读回 stack 和各层 PR，核实 stack 编号、成员顺序、base 及 head SHA。超时、冲突或响应不明确时，先重新查询，已完成就复用，只在最新证据仍支持同一动作时重试。无法连接时保留已建 PR，报告「PR 已提交，stack 待连接」。下次从读回结果恢复。
