---
name: run-issues
description: "Implement a directory of tickets end to end, each in its own fresh Claude session. Reads the tickets' dependency edges, works the frontier in order, stops at human review gates. Invoke with /run-issues <path-to-issues-dir>."
disable-model-invocation: true
---

# Run Issues

Implement every ready ticket in a directory, one at a time, each in a brand-new session.

The argument is a ticket directory — typically `.scratch/<feature>/issues/`, as produced by
`/to-tickets`. If the user gave a feature directory instead, look for `issues/` inside it.

## Why this is split in two

A ticket's `**Blocked by:**` line is prose, and in practice it varies a lot:

```
**Blocked by:** None — can start immediately.
**Blocked by:** [01](01-vault-store.md), [05](05-beat-2-material.md)
**Blocked by:** 01, and Ben's review of Phase 1 (01 + 02)
```

That third one is the reason a shell script cannot own this. "Ben's review" is not a ticket, it is
an instruction to stop and get a human. Reading edges like that is your job.

`runner.sh` owns the other half: launching one ticket in a session with no history. That matters
because a ticket is sized to fit one fresh context window — chaining them inside a single session
means ticket four is being implemented through a compacted summary of tickets one through three,
which is exactly the failure the ticket sizing was meant to prevent.

So: **you read and decide, the script executes.** Do not implement tickets yourself in this
session. Your context is already partly spent, and it accumulates across tickets — the thing the
whole arrangement exists to avoid.

## Process

### 1. Read the directory

Read every `NN-*.md` and the `README.md` if there is one. The README usually carries a dependency
table and any phase structure, which is faster to read than reconstructing it from six files.

Note each ticket's number, title, `Blocked by`, and `Status`.

Match `Status` on its prefix, not equality — `done — src/app/foo.tsx` is done. Anything that is not
`ready-for-agent` and not `done` is unusual; mention it rather than guessing.

### 2. Find the verify command

Tickets say what to build, not how the project checks itself. Look in CLAUDE.md, README, or
package.json scripts for the real gate, and prefer the cheapest one that would actually catch a
broken ticket.

Some projects have no test suite at all — a type-check or a build is then the only automatic gate
there is, and it is worth being explicit with the user that it is a weak one, because it changes
how much they should trust a long unattended chain.

### 3. Build the order, then show it

Work the **frontier**: a ticket is runnable when every ticket it is blocked by is done. Order the
runnable ones by number; blockers come first by construction of `/to-tickets`.

Watch for two things the numbering hides:

- **Human gates.** A `Blocked by` that names a person, a review, or a decision is a hard stop. So
  is a `⏸` row in the README's table. Everything downstream of it waits, no matter how many
  tickets are marked ready.
- **Tickets that are parallel on paper.** When several tickets share a blocker and touch the same
  area, running them in sequence is usually better anyway: the first one establishes the pattern
  and the rest follow it, whereas parallel sessions each invent their own and you get to reconcile
  three versions afterward. Say so and let the user choose. If they do want parallel, each session
  needs its own git worktree or they will fight over the same files.

Show the plan before running anything — the ordered list, the gate positions, the verify command.
The user is agreeing to an unattended chain of edits to their repo, so this is the moment to catch
a wrong edge, not after four commits.

### 4. Run, one ticket at a time

```bash
bash ~/.claude/skills/run-issues/runner.sh \
  --ticket <path> \
  --verify "<verify command>"
```

Call it once per ticket and branch on the exit code:

| Code | Meaning | What to do |
|------|---------|------------|
| 0 | done, verified, Status rewritten | Continue to the next ticket |
| 2 | not `ready-for-agent`, skipped | Fine — say so and continue |
| 3 | verify command fails | **Stop the chain.** Read the `.verify.log`, report it |
| 4 | session ended without marking it done | **Stop the chain.** Read the session's closing message |

Stop on 3 and 4 rather than pressing on. Later tickets are built on the assumption that earlier
ones landed, so continuing past a failure means the next session starts from a broken base and its
own failure tells you nothing about its own work.

Pass `--model` only if the user asked for a specific one.

Between tickets, re-read the ticket that just ran. It should now have its boxes ticked and a
commit behind it. If the file says done but nothing was committed, treat that as a code-4 stop.

### Where the logs go

**Do not pass `--log-dir`.** The default is the convention, and a caller free to name the
directory is a caller who will name it something different every time — `phase2` one session,
`trial-02` the next, a bare timestamp when nobody thought about it at all.

Each run writes two files, flat, into `<feature>/runs/`:

```
runs/20260817-011043-03-associate-widget.jsonl        the full session stream
runs/20260817-011043-03-associate-widget.verify.log   the verify command's output
```

Timestamp first so sorting by name sorts by time, ticket second so `ls` reads as a history.
A rerun never overwrites the run it repeats, and pruning is `ls runs/*.jsonl | head -n -10 |
xargs rm`. A skipped ticket writes nothing.

Add `runs/` to the project's `.gitignore` if it is not there. `.scratch/` is often partly
tracked — the tickets and the spec belong in git — and these transcripts do not: they run to
megabytes each, because every tool result the session saw is in them verbatim.

**Reading them.** For a code-3 or code-4 stop, read the `.verify.log` first: it is small and it
is usually the whole answer. Reach for the `.jsonl` only when the verify log does not explain
the failure, and even then query it rather than reading it — `jq -r 'select(.type=="result") |
.result' <file>` gives the session's own closing account in a few hundred tokens. Never read one
whole. Pulling a megabyte of another session's tool output into this one undoes the context
isolation the fresh-session design exists for.

Override `--log-dir` only when the user asks for the logs somewhere specific. It now names the
directory the files land in, not a per-batch subdirectory.

### 5. Report

Per ticket: what ran, the exit code, the commit. Then where the chain stopped and why — a gate, a
failure, or the end of the frontier. If a gate stopped it, name what the user has to look at
before the rest can go.

## When permissions get in the way

`runner.sh` uses `--permission-mode acceptEdits`, which auto-approves file edits but still sends
Bash through the project's allowlist. A headless session cannot answer a permission prompt, so a
missing allowlist entry shows up as the agent failing to build or commit.

The fix is to add the specific command to `.claude/settings.local.json`, not to reach for
`--dangerously-skip-permissions`. Projects tend to keep real quality gates in PostToolUse hooks,
and skipping permissions is often what quietly disables them for the entire run.
