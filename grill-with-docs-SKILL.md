---
name: grill-with-docs
description: A relentless interview to sharpen a plan or design, checkpointed to a capture file as it goes, which also creates docs (ADR's and glossary).
disable-model-invocation: true
---

Run a `/grilling` session, using the `/domain-modeling` skill.

`/grilling` asks the whole frontier in one round. `/domain-modeling` keeps the glossary honest and offers an ADR when a decision is genuinely hard to reverse. Neither of them writes down the interview itself, which is what the rest of this file is for.

## The capture file

Long interviews fill up context. Anything you hold only in your head will eventually get misremembered, conflated, or quietly dropped, and the user will have spent their attention for nothing. So the file on disk is the source of truth, not your context. The user should never have to ask you to save progress.

Before asking the first question, create `brainstorms/{YYYY-MM-DD}-{topic-slug}.md` (make the folder if it isn't there; get the date with `date +%F` if you don't already know it) containing:

- Title, date, and a one-line goal for the session
- A pointer to any prior session this one continues, plus which of its decisions this round may overturn
- An empty "Open flags" section
- Round 1's questions, once you've composed them

Then tell the user the path in one line and post the round.

## Checkpoint per round

`/grilling` batches the frontier, so answers arrive a round at a time. The round is therefore the natural checkpoint unit, and it gives the same guarantee as checkpointing per answer: when a round closes, nothing said in it survives only in context.

After every round of answers, before you compose the next round:

- Append an entry per question: its topic, the options you offered, your recommendation, and what the user actually decided. Keep their wording where the wording is the decision.
- Log anything they could not answer as a flag with the person who can answer it. Don't stall on it.
- Go back and correct earlier entries a later answer invalidated. A capture file that still asserts a superseded decision is worse than no file, because the next reader trusts it.
- Note questions the user skipped, and carry them into the next round rather than treating silence as assent.

Only then recompute the frontier.

## Structure

```
# {Topic}: Grilling 记录
Date: {date} · Goal: {one line}

## Summary / 关键决策
(running synthesis, updated each round)

## Q&A log
### Round 1
**Q1 · {title}** — Options: {...} · Recommended: {...} · Decided: {...}
...

## Open flags
- {item} -> {who can answer}
```

## At the end

Read the capture file back and reconcile contradictions and gaps before you touch anything else.

Then place the durable decisions where the project keeps them. If the repo has its own conventions (a decision-records index, an architecture doc, a route table, a glossary), those conventions win over anything invented here, and the capture file's job is to feed them. `/domain-modeling` owns `CONTEXT.md`, which stays a glossary and nothing else. The raw Q&A log always stays in `brainstorms/`.

Record the *why* alongside the *what*. A decision without its rejected alternatives reads, six months later, as an arbitrary choice nobody dares revisit.
