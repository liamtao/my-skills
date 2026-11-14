---
name: a2b2-stacked-branches
description: "Manage Ben's A2B2 stacked branches: fetch main, verify merged PRs, restack local descendants, delete fully merged local branches, or create a named child branch. Use for branch maintenance and choosing stacked PR delivery scope, not implementation, releases or ordinary PR reviews."
---

# A2B2 stacked branches

Keep development continuous while each PR has a fixed review scope. After a
lower layer lands, move only the next layer's own commits to `origin/main`;
keep higher layers on their surviving parents. Communicate in Chinese.

## Select the requested operation

- `检查` / `check`: fetch remote information and report the graph and PR states.
  Keep local branches and configuration unchanged.
- `整理` / `sync`, or a bare invocation: fetch, verify, restack the selected local
  chain, then delete its fully merged local branches.
- `新建 <topic>` / `new <topic>`: refresh and reconcile the parent chain, then
  create a named child branch and record its dependency.
- `PR 策略` / PR preparation: inspect the ancestor chain and help choose separate
  dependent PRs or one combined PR to main. This mode is read-only and does not
  run sync, create branches or authorize remote changes.
- Honor a narrower request, such as fetching main only. Creating or editing this
  skill does not invoke branch maintenance.

Sync and new authorize the described local Git changes; check and PR strategy
selection remain read-only. These modes do not authorize pushes, PR
creation/edits/merges, remote branch deletion, deployment,
or Linear status changes. If those actions are requested too, use the applicable
repository workflow and existing authorization. A local rebase does not update
the remote PR automatically.

## Inspect before changing branches

1. Read repository guidance, including A2B2's pre-push skill and its PR preparation
   reference before branch selection. Inspect the Git root, active branch,
   status including untracked files, worktrees, remotes and local branch tips.
   Resolve the actual GitHub host/repository from the remote.
2. Default scope is the active topic branch, its proven ancestors and descendants.
   Other stacks can be audited when requested; do not rewrite or delete unrelated
   branches. If the active branch is `main` and no chain is identified, report
   candidates and ask which chain to maintain. Protect `main`, `sit`, `prod`,
   other release branches and other people's work.
3. Save the original tips and known parent boundaries before fetching. Fetch
   `origin` without pruning so deleted remote refs do not erase useful evidence.
   Confirm `refs/remotes/origin/main` resolves and the fetch succeeded. Use that
   ref as the main baseline; leave a divergent local `main` intact.
4. Discover available connected GitHub read tools first. If insufficient, use
   authenticated `gh` with an explicit repository/host. Retrieve every relevant
   PR, including closed ones and pagination, and record its number, URL, state,
   base, merged time, head SHA and landed commit SHA.
5. Establish the chain from recorded metadata, PR base relationships and Git
   ancestry together. Read [restacking.md](references/restacking.md) before any
   rebase, deletion or adoption of an existing chain. Names and dates alone do
   not establish ancestry. Report ambiguous edges and keep that subtree intact.

Report an eligible before/after graph and then perform the requested local
operation without asking again for already authorized actions. With dirty files,
an ongoing Git operation, or a branch checked out in another worktree, complete
the read-only audit and defer affected mutations. Preserve the files and other
worktrees; do not auto-commit, stash, clean or reset them.

## Choose PR delivery scope

When preparing a PR whose branch includes ancestor-layer changes not yet landed
in main, read the selected checkout's
`.agents/skills/a2b2-pre-push-checks/references/pull-request.md`, section
"Choose stacked PR scope". Apply its strategy question before selecting the base
or running base-dependent checks. Reuse an explicit choice for the same target
branch and ancestor scope. An ambiguous dependency needs clarification, not a
guessed PR base. Strategy selection alone does not run branch maintenance or
expand authorization for pushes, PR edits or force-pushes.

## Detect parent updates

During check and sync, compare each proven parent-child edge against the latest
parent commit already included in the child, not just its saved boundary. Show
which descendants lack parent updates, the old boundary and target parent tip.
Read [restacking.md](references/restacking.md#detect-and-propagate-parent-updates)
for detection and replay rules, including parents that have not landed in main.

Check only reports needed rebases. Sync and new reconcile eligible descendants
bottom-up using backups and verified boundaries, without asking again for the
local rebases already authorized. Report dirty or occupied worktrees, ambiguous
boundaries and conflicts as pending; never describe an unchanged remote PR as
updated by a local rebase.

## Reconcile merged layers

Classify each branch as open/unmerged, fully landed in main, merged with extra
local commits, merged elsewhere, or unknown. A closed PR, missing remote branch
or `git branch --merged` alone cannot prove that a squash-merged PR is in main.

Verify the PR's landed commit is reachable from fresh `origin/main` and its
recorded merged head covers the local branch tip. Keep branches with extra
unmerged commits or ambiguous reused PR histories. If GitHub evidence or the
required commit objects are unavailable, report unknown and defer that subtree.

For an eligible chain, create local backup refs, restack bottom-up using verified
old boundaries, compare each layer's old/new changes, and update dependency
metadata. Follow the detailed conditions in [restacking.md](references/restacking.md).
On conflict, abort that rebase, retain earlier successful changes and all backup
refs, report the partial state, and leave cleanup pending.

After the whole affected chain verifies, automatically delete its fully landed
local branches. First detach surviving descendants from those parents and switch
off any branch being deleted. Keep branches occupied in another worktree or
containing additional commits. Delete no remote branches. Report preserved
backup refs and every skipped deletion.

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
Clearly distinguish local completion from remote PR state. List any next remote
actions, including PR retargeting and a possible authorized `--force-with-lease`
push after the required checks. Do not call an unchanged remote PR synchronized.

Example requests:

```text
$a2b2-stacked-branches 检查当前叠加链
$a2b2-stacked-branches 整理当前叠加链
$a2b2-stacked-branches 新建 Mobile 字体优化分支，接着当前版本做
$a2b2-stacked-branches 从 main 新建独立的 Portal 按钮间距分支
```
