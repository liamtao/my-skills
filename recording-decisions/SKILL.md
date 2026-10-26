---
name: recording-decisions
description: Use when the user wants to save, persist, archive, or record key decisions from a session into the project decision log, or to revise/update/reverse a previously recorded decision. Triggers include "记录决策", "保存这次的决策", "归档这次决策", "save our decisions", "update that earlier decision".
---

# Recording Decisions

## Overview
Persist a session's key decisions into a git-tracked, per-module decision log so a FUTURE session can quickly grasp the logic and prior decisions behind a module. Three layers (progressive disclosure):

- **Host instruction file** (selected below): references the index document and lists *which modules* are covered. No decision details.
- **Index document** `docs/decisions/README.md`: one row per module — link + a one-line hook of the logic it covers.
- **Module docs** `docs/decisions/<module>.md`: the actual decisions, each as **Decision + Why**.

Core principle: capture the *why* (the rationale that is expensive to re-derive), keep the always-loaded layers tiny, push detail down.

## Select the host instruction file

Use an explicit user/repository choice first. Otherwise, select from the current host's documented instruction-loading convention: `AGENTS.md` for Codex, `CLAUDE.md` for Claude Code. A skill's author, plugin name, or mention of Claude is not evidence of the current host.

Read the selected file if it exists and preserve its existing instructions; create it only when the host convention is established. Do not create both files or replace another host's existing file. If the host convention is unknown or no instruction file is supported, add the pointer to the existing project README instead. Do not claim that a file is automatically loaded merely because it exists.

## When to Use
- User asks to save / persist / archive / record this session's decisions.
- User asks to update, revise, or reverse a previously recorded decision.
- A work chunk produced a non-obvious decision worth keeping for future iterations.

Skip ephemeral or trivial choices, and anything the code or git history already makes obvious.

## Procedure
1. **Extract** the keep-worthy decisions. Each = a one-line **Decision** + a **Why**. Add the date and touched files where useful.
2. **Assign a module** to each: a stable kebab-case slug for the code area or feature (e.g. `agent-tasks`, `skills`). FIRST read the existing `docs/decisions/*.md` and reuse those slugs — do not fork a near-duplicate module.
3. **Write each module doc** `docs/decisions/<module>.md`:
   - New decision → append an entry.
   - Revises/reverses a prior entry → **edit that entry in place** (never leave two contradicting entries). If the old decision had shipped or was referenced elsewhere, keep a `**Superseded <date>:** <old>` note so the change is traceable; if it never shipped, overwrite cleanly.
4. **Update the index** `docs/decisions/README.md`: ensure one row per module — `- [<Module title>](<module>.md) — <one-line hook of the logic/decisions it covers>`. Create the file if missing.
5. **Update the selected host instruction file (or README fallback)**: ensure a short "Decision Records" section that *references the index document* and names the covered modules (one line each). It must NOT contain specific decisions or logic — pointers + module coverage only. Preserve unrelated content.

## Entry format (module doc)
```markdown
## <Short decision title> — <YYYY-MM-DD>
**Decision:** <what was decided>
**Why:** <rationale that is expensive to re-derive>
**Where:** <files/areas> (optional)
```

## Quick reference
| Layer | File | Holds | Rule |
|---|---|---|---|
| Host entry | selected instruction file / README | pointer to index + module names | no details; loading depends on host |
| Index | `docs/decisions/README.md` | module → link + 1-line hook | no details |
| Detail | `docs/decisions/<module>.md` | Decision + Why | edit in place on revision |

## Common mistakes
- Putting decision details into the host entry or the index (defeats progressive disclosure). Keep both pointer-only.
- Creating `CLAUDE.md` in Codex without an explicit user/repository requirement, or assuming every host loads the same instruction filename.
- Recording the *what* but not the *why*.
- Appending a new entry that contradicts an old one instead of editing the old one in place.
- Inventing a new module slug when an existing one fits.
