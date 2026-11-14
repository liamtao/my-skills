# Verified restacking and local cleanup

Read this before modifying a chain. Use the repository's actual PR evidence and
Git graph; the commands below are templates, not a bulk branch-cleanup script.

## Persist the dependency boundary

For branches created or confidently adopted by this skill, store two local Git
config keys. Their values are a parent branch name (or `origin/main`) and the
exact parent commit already included in this child:

```bash
git config --local "branch.${child}.a2b2-stack-parent" "$parent"
git config --local "branch.${child}.a2b2-stack-base" "$boundary_sha"
```

Use quoted, validated values; `child` and `parent` are task-specific variables.
The boundary is a commit, not a movable ref or PR number. Read these keys on later
runs, validate them against the graph and PR relationships, and refresh them only
after a verified migration. Metadata lives in this checkout's Git configuration,
not in tracked product files. It is not distributed by clone or push.

After a local-only migration, a remote PR can still name the deleted old parent.
Use the verified local metadata and backup map to recognize this pending remote
transition on the next run. Do not reconstruct the old dependency from the stale
PR base or replay its commits. Report the needed remote retarget separately.

For an existing unrecorded chain, confirm PR bases and a unique common ancestor.
The merge base can establish a boundary only for a demonstrably append-only,
linear parent history. If the parent was rewritten and its prior boundary is
unknown, use a preserved old ref/reflog and PR evidence, or ask. Do not infer the
boundary from today's parent tip: the child may not yet include that tip.
Inspect the entire proposed `boundary..child` range for inherited parent changes.
If the child incorporated parent updates since the recorded boundary, advance
it only to the latest verified parent commit already included in that child.
Defer histories with merge commits rather than flattening them implicitly.

Before any rewrite or deletion, preserve every affected original tip and old
boundary under `refs/a2b2-stack-backups/<unique-run-id>/<safe-label>` using
`git update-ref`. Keep a branch-to-ref and boundary map in the task report or
work state. Backup refs survive branch deletion and are not normal topic branches.
Keep them until the user requests their cleanup.

## Prove full landing

A local branch is eligible for cleanup when all of these hold:

1. A PR from the correct repository/head is confirmed merged, with a recorded
   landed commit reachable from fresh `origin/main`. For indirect landing through
   another base, prove that chain too; a PR merged elsewhere alone is insufficient.
2. The local tip equals or is an ancestor of the PR's verified head at merge time.
   A descendant with later commits is only partially landed. Reused branch names
   require checking every relevant PR and the exact commit range.
3. There is no newer open PR or unclassified work on that local branch. A later
   revert in main remains an intentional main change; do not reapply the old PR.

Prefer the PR's recorded merged revision or PR commit records over a mutable live
branch ref. Verify the landed commit with `git merge-base --is-ancestor`. A
`merge_commit_sha` on an unmerged PR can be a test merge, so check merged state
first. Squash and rebase merges change commit identity: requiring the original
head to be an ancestor of main would incorrectly reject legitimate landings.

If the current local tip has extra unmerged commits after an old merged PR,
preserve it and its descendants. Report the tail and the need to identify a new
delivery boundary; do not silently discard that tail or adopt a historical PR as
proof of complete landing.

## Detect and propagate parent updates

For each proven edge `A -> B`, capture A's current tip, B's original tip and the
latest verified A commit already included in B. The saved boundary is a starting
point: if B already incorporated later A commits, verify and use that later
boundary before selecting B's own range. If A's current tip is an ancestor of B,
no parent update is missing. Check mode reports this without updating metadata.

If A has advanced beyond the included boundary and its tip is not in B, report
B as needing a rebase and include B's proven descendants in the impact report.
This applies even when A has no PR or its PR remains open. Never use A's newer
tip as the old exclusion boundary unless it is already included in B.

In sync/new mode, preserve all original tips and boundaries before moving any
layer. Rebase B's own `included_a..old_b` range onto A's reconciled tip, verify
it, then move C's own range from its saved B boundary onto the new B tip. Repeat
for eligible descendants and refresh metadata only after verification. An empty
child remains a valid planned dependency and follows its parent with an empty
own range. Leave unrelated siblings outside the selected proven subtree alone.

For rewritten parent histories, require evidence that maps the preserved old
boundary to the current parent. A missing boundary or unclassified inherited
commits makes that edge ambiguous: report it and defer its subtree. Do not infer
replay ranges from today's parent tip or resolve divergence by discarding work.
Retain the existing conflict, worktree and remote-authorization safeguards.

## Restack bottom-up

Example: `main -> A -> B -> C`; A is fully landed by squash, B and C remain open.
Before moving anything, capture:

- `old_b` and `old_c`: original B and C tips.
- `base_b`: latest verified A commit already included in original B.
- `base_c`: latest verified B commit already included in original C.
- `main_tip`: the freshly fetched `origin/main` commit.

The target is `main -> B' -> C'`, not `main -> B'` and `main -> C'` separately.
Use full saved SHAs for old boundaries, including when local branch names move:

```bash
git rebase --onto "$main_tip" "$base_b" "$branch_b"
# Verify B before proceeding; capture its resulting tip as new_b.
git rebase --onto "$new_b" "$base_c" "$branch_c"
```

After verification, B's metadata becomes parent `origin/main`, base `main_tip`;
C's becomes parent B, base `new_b`. If A and B both landed, first prove both tips
are covered, then move only C's own range to main. For multiple children, process
each proven edge; do not fabricate a single chain from siblings.

When no parent PR landed, keep the parent relationship. A requested sync may
refresh the bottom layer onto new main, then restack descendants on updated
parents. If tips and boundaries are already current, leave them unchanged.
Capture all original boundaries before the first rebase; using an already
rebased parent's new SHA as the exclusion boundary can replay old parent commits.

If GitHub's native stack manager already restacked remote branches, inspect those
tips before rewriting locally. Fast-forward clean, behind-only local branches
where the verified remote state is authoritative, then reconcile metadata. Keep
divergent local/remote histories intact until local-only work and boundaries are
understood. Do not combine server and manual restacks blindly or push stale tips
over a server-managed result.

For every moved layer:

- Verify the new parent is an ancestor of the child.
- Compare `git range-diff old_base..old_tip new_base..new_tip` and the actual
  layer diffs. Account for dropped, changed or newly empty commits; do not use
  `--skip` or accept a changed range merely to finish.
- Confirm inherited landed changes are excluded from the new layer's range and
  its own intended changes remain. Check `git diff --check` and run proportionate
  affected checks where the new base changes integration behavior. Report any
  unrun product checks separately from Git graph verification.

On conflict, abort the current rebase and stop that subtree. Do not choose
ours/theirs globally. A failed post-rebase verification also stops cleanup;
retain the resulting and original refs for diagnosis. Report any earlier layers
that completed, rather than claiming the whole operation was rolled back.

## Delete fully landed local branches last

After the entire affected chain verifies:

1. Recheck that surviving descendants no longer depend on each deletion target
   and their metadata names the new parent. Keep any target whose child could not
   be safely migrated, including a child checked out in another worktree.
2. Recheck worktree occupancy, branch tip against the inspected SHA, landing
   evidence and backup-ref existence immediately before deletion. Skip protected
   branches, unknown ownership or any concurrent tip change.
3. If deleting the current branch, switch the clean worktree to the intended
   surviving branch. With no surviving topic, use clean local main only when it
   equals fresh main; otherwise detach at the fetched main SHA. Preserve a
   divergent local main. For `new`, create from that verified main baseline.
4. Try `git branch -d -- <branch>`. Git may reject a valid squash/rebase landing
   because the original commits are not ancestors of HEAD. When every proof above
   holds and the rejection is only the not-merged ancestry check, the user's
   requested local cleanup authorizes `git branch -D -- <branch>`. Never use
   forced deletion to bypass extra commits or worktree occupancy.

Report branch deletion separately from retained backup refs. Remote branches and
PR settings remain unchanged unless separately requested.

Primary references, consulted 2026-11-09:
[Git rebase](https://git-scm.com/docs/git-rebase),
[GitHub pull request API](https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request),
[GitHub stacked PRs](https://docs.github.com/en/pull-requests/reference/stacked-pull-requests).
