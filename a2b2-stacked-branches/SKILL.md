---
name: a2b2-stacked-branches
description: "Manage Ben's A2B2 stacked branches: inspect GitHub-native stacks, sync or restack local branches, verify merged PRs, clean up landed worktrees and branches, or create a child branch. Use for branch maintenance and stacked PR delivery strategy, not implementation, releases or ordinary PR reviews."
---

# A2B2 stacked branches

Keep each PR's review scope focused on its own layer. For published native
stacks, reconcile local branches with GitHub's verified result first. Use
saved Git boundaries to manage unpublished layers and ordinary PR chains.
Communicate in Chinese.

## Select the requested operation

- `检查` / `check`: fetch remote information and report the graph and PR states.
  Keep local branches and configuration unchanged.
- `整理` / `sync`, or a bare invocation: fetch, reconcile the selected local
  chain with verified remote results or local restacking, then delete its
  fully landed local branches and their eligible clean linked worktrees.
- `清理 <PR or branch>` / `cleanup <PR or branch>`: verify the named targets and
  run [post-merge cleanup](references/restacking.md#delete-fully-landed-local-branches-last)
  for standalone PRs or landed stack layers. Defer a target if a surviving
  dependent branch still needs to be restacked.
- `新建 <topic>` / `new <topic>`: refresh and reconcile the parent chain, then
  create a named child branch and record its dependency.
- `PR 策略` / PR preparation: inspect the ancestor chain and help choose separate
  dependent PRs or one combined PR to main. This mode is read-only and does not
  run sync, create branches or authorize remote changes.
- Honor a narrower request, such as fetching main only. Creating or editing this
  skill does not invoke branch maintenance.

Sync, new and cleanup authorize the described local Git changes. Check and PR
strategy selection remain read-only. These modes do not authorize pushes, PR
creation/edits/merges, remote branch deletion, deployment,
or Linear status changes. If those actions are requested too, use the applicable
repository workflow and existing authorization. Use Git fetch and verified local
ref updates for this skill's `sync`. The CLI's `gh stack sync` also pushes and
can create or update a remote stack.

## Inspect before changing branches

1. Read repository guidance, including A2B2's pre-push skill and its PR preparation
   reference before branch selection. Inspect the Git root, active branch,
   status including untracked files, worktrees, remotes and local branch tips.
   Resolve the actual GitHub host/repository from the remote.
2. Use the named PRs or branches when the user scopes cleanup explicitly.
   Otherwise use the active topic branch, its proven ancestors and descendants.
   Other stacks can be audited when requested; do not rewrite or delete unrelated
   branches. If the active branch is `main` and no chain is identified, report
   candidates and ask which chain to maintain. Protect `main`, `sit`, `prod`,
   other release branches and other people's work.
3. Save the original local and remote-tracking tips and known parent boundaries
   before fetching. Fetch with `git fetch --no-prune origin` to retain remote
   refs as evidence after GitHub deletes a branch.
   Confirm `refs/remotes/origin/main` resolves and the fetch succeeded. Use that
   ref as the main baseline; leave a divergent local `main` intact.
4. Discover available connected GitHub read tools first. If insufficient, use
   authenticated `gh` with an explicit repository/host. Retrieve every relevant
   PR, including closed ones and pagination, and record its number, URL, state,
   base, merged time, head SHA and landed commit SHA. For published layers, read
   [GitHub stack membership](https://docs.github.com/en/pull-requests/reference/stacked-pull-requests-apis-and-webhooks)
   via REST or GraphQL. Use the stack's base and ordered entries to establish
   the published chain. A tool that omits stack data or a failed query leaves
   membership unknown.
5. Verify the published PR graph against fetched heads and Git ancestry. Use
   PR bases and saved local boundaries to establish ordinary or unpublished
   edges. Read [restacking.md](references/restacking.md) before moving or
   deleting branches. Preserve a published subtree whose membership or old
   boundaries remain ambiguous.

Report an eligible before/after graph and then perform the requested local
operation without asking again for already authorized actions. Defer mutations
for dirty worktrees or ongoing Git operations. A branch checked out in another
worktree blocks ref updates. During cleanup, remove an eligible clean linked
worktree first using the [cleanup procedure](references/restacking.md#delete-fully-landed-local-branches-last).

## Choose PR delivery scope

When preparing a PR whose branch includes ancestor-layer changes not yet landed
in main, read the selected checkout's
`.agents/skills/a2b2-pre-push-checks/references/pull-request.md`, section
"Choose stacked PR scope". Apply its strategy question before selecting the base
or running base-dependent checks. Reuse an explicit choice for the same target
branch and ancestor scope. An ambiguous dependency needs clarification, not a
guessed PR base. Strategy selection alone does not run branch maintenance or
expand authorization for pushes, PR edits or force-pushes.

When the chosen scope is separate dependent PRs, recommend linking the
verified same-repository PR chain in GitHub after the PRs are created through
the existing submission workflow. Preserve the team's base, draft, review and
check requirements. Linking is a separate GitHub write and needs authorization
covering the affected PRs. GitHub can merge a stack from the bottom up, so
merging an upper PR also merges any unmerged layers below it. Check the actual
merge scope against the authorization if a merge is separately requested.
[GitHub creation and linking guide](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/creating-stacked-pull-requests)

## Detect and reconcile parent updates

During check and sync, compare each proven parent-child edge against the latest
parent commit already included in the child, not just its saved boundary. Show
which descendants lack parent updates, the old boundary and target parent tip.
Read [restacking.md](references/restacking.md#detect-and-propagate-parent-updates)
for detection and replay rules, including parents that have not landed in main.

Check reports which layers already moved on GitHub, which need local sync, and
which still need a rebase. For native stacks, apply
[Reconcile a GitHub-native stack](references/restacking.md#reconcile-a-github-native-stack)
before choosing any replay range. For ordinary chains and eligible unpublished
descendants, sync and new use the existing bottom-up restack. Report worktree
blockers, ambiguous boundaries and conflicts as pending.

## Reconcile merged layers

Classify each branch as open/unmerged, fully landed in main, merged with extra
local commits, merged elsewhere, or unknown. A closed PR, missing remote branch
or `git branch --merged` alone cannot prove that a squash-merged PR is in main.

Use [full landing evidence](references/restacking.md#prove-full-landing) to
verify both the landed commit and every local change, including when a
consolidated PR carried the branch's changes under different commit IDs.

For an eligible chain, preserve local backup refs, reconcile bottom-up, compare
each layer's old and new changes, and update dependency metadata. Follow the
detailed conditions in [restacking.md](references/restacking.md).
On conflict, abort that rebase, retain earlier successful changes and all backup
refs, report the partial state, and leave cleanup pending.

After the whole affected chain verifies, apply the
[cleanup procedure](references/restacking.md#delete-fully-landed-local-branches-last)
to fully landed branches in scope. Remove eligible clean linked worktrees before
deleting their branches. Report removed worktrees, backup refs and every skipped
deletion.

## Create a branch

Use `codex/<surface>-<type>-<topic>` or, when supplied,
`codex/<surface>-<type>-<ticket>-<topic>`.

- Surfaces include `mobile`, `portal`, `marketing` and `repo`.
- Use `ui` for visual adjustments, `ux` for interaction changes and `fix` for bugs.
- Use lowercase, concise kebab-case. Example:
  `codex/mobile-ui-a2b-123-dynamic-type`.
- Omit dates and stack positions by default. Validate with
  `git check-ref-format --branch` and check both local and remote collisions.
  Reuse an existing branch only when it is demonstrably the same task; otherwise
  choose a meaningful qualifier. Do not overwrite or silently rename branches.

Default parent is the current reconciled topic branch when the user wants to
continue its version. If it is fully landed with no remaining layer, start from
`origin/main`. If the user says the new task is independent, start from
`origin/main`. Ask only when the topic or intended parent remains ambiguous.
An empty topic branch with no commits can still be the parent of planned work;
say when the dependency is only planned.

Create with `git switch --no-track -c <new-name> <verified-parent-tip>` on a clean
worktree. Record the parent and exact boundary in local Git config as described
in the reference. Do not set the parent's remote branch as the child's tracking
upstream. Advise the future PR base: the open parent branch, or `main` after it
lands. Dependent PRs are drafts under the repository's existing PR guidance.
Suggest keeping the pending stack to 2–3 layers; do not block new work solely
because it exceeds that recommendation.

## Completion

Report fresh main SHA, scope and PR evidence; the resulting chain; created,
rebased, deleted and preserved branches; verification results and backup refs.
Report which PR bases and heads GitHub has already updated and any remote work
still pending. For a manual restack, report any outstanding retarget and push
after the applicable team checks and authorization.

Example requests:

```text
$a2b2-stacked-branches 检查当前叠加链
$a2b2-stacked-branches 整理当前叠加链
$a2b2-stacked-branches 清理已合入的 PR #123，允许归档它对应的 Codex 聊天
$a2b2-stacked-branches 新建 Mobile 字体优化分支，接着当前版本做
$a2b2-stacked-branches 从 main 新建独立的 Portal 按钮间距分支
```
